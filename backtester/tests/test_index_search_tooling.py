"""The index helper scripts: ollama auto-start, the idle rebuild decision, and library search.

No test touches a real ollama or embeds anything. Servers, clocks, load and processes are
injected or patched, so these are deterministic and offline. What each one defends:

* `ollama_ensure` never talks to a non-local host, only launches a server when it is allowed
  to, and reports a missing model instead of downloading ~670 MB;
* `idle` starts a rebuild only when stale AND idle AND unlocked AND the model is installed, and
  its throttle stops a burst of searches from re-hashing the tree;
* `search.run_query` never prints, falls back to keyword with a reason, and loads nothing at import.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "index"))

import idle  # noqa: E402
import ollama_ensure as oe  # noqa: E402
import search  # noqa: E402


class EnsureTests(unittest.TestCase):
    def test_a_remote_host_is_refused_before_any_request(self):
        with mock.patch.object(oe, "installed_models") as probe:
            status = oe.ensure(base="http://10.0.0.5:11434")
        self.assertFalse(status.ok)
        self.assertIn("local", status.message)
        probe.assert_not_called()

    def test_model_name_and_latest_tag_are_the_same_model(self):
        self.assertTrue(oe.model_matches(["mxbai-embed-large:latest"], "mxbai-embed-large"))
        self.assertTrue(oe.model_matches(["mxbai-embed-large"], "mxbai-embed-large:latest"))
        self.assertFalse(oe.model_matches(["nomic-embed-text:latest"], "mxbai-embed-large:latest"))

    def test_a_running_server_with_the_model_is_ready_and_nothing_is_started(self):
        popen = mock.Mock()
        with mock.patch.object(oe, "installed_models", return_value=["mxbai-embed-large:latest"]):
            status = oe.ensure(popen=popen)
        self.assertTrue(status.ok)
        self.assertFalse(status.started)
        popen.assert_not_called()

    def test_a_stopped_server_is_started_then_waited_for(self):
        answers = iter([None, None, ["mxbai-embed-large:latest"]])
        popen = mock.Mock()
        with mock.patch.object(oe, "installed_models", side_effect=lambda *a, **k: next(answers)), \
                mock.patch.object(oe, "start_server", return_value="the Ollama app") as start:
            status = oe.ensure(sleep=lambda s: None, popen=popen)
        start.assert_called_once()
        self.assertTrue(status.ok)
        self.assertTrue(status.started)

    def test_start_false_never_launches_anything(self):
        with mock.patch.object(oe, "installed_models", return_value=None), \
                mock.patch.object(oe, "start_server") as start:
            status = oe.ensure(start=False)
        start.assert_not_called()
        self.assertFalse(status.reachable)

    def test_a_server_that_never_answers_is_reported_not_raised(self):
        clock = iter([0.0, 0.0, 1.0, 100.0, 200.0])
        with mock.patch.object(oe, "installed_models", return_value=None), \
                mock.patch.object(oe, "start_server", return_value="`ollama serve`"), \
                mock.patch.object(oe.time, "monotonic", side_effect=lambda: next(clock)):
            status = oe.ensure(wait=5, sleep=lambda s: None)
        self.assertFalse(status.ok)
        self.assertTrue(status.started)
        self.assertIn("did not answer", status.message)

    def test_nothing_to_launch_is_said_plainly(self):
        with mock.patch.object(oe, "installed_models", return_value=None), \
                mock.patch.object(oe, "start_server", return_value=""):
            status = oe.ensure()
        self.assertIn("no Ollama app", status.message)

    def test_a_missing_model_is_reported_with_the_pull_command_and_not_downloaded(self):
        with mock.patch.object(oe, "installed_models", return_value=["nomic-embed-text:latest"]), \
                mock.patch.object(oe, "pull_model") as pull:
            status = oe.ensure()
        pull.assert_not_called()
        self.assertFalse(status.ok)
        self.assertTrue(status.reachable)
        self.assertIn("ollama pull mxbai-embed-large:latest", status.message)

    def test_pull_true_downloads_then_rechecks(self):
        seen = [["nomic-embed-text:latest"], ["nomic-embed-text:latest", "mxbai-embed-large:latest"]]
        with mock.patch.object(oe, "installed_models", side_effect=lambda *a, **k: seen.pop(0) if len(seen) > 1 else seen[0]), \
                mock.patch.object(oe, "pull_model", return_value=True) as pull:
            status = oe.ensure(pull=True)
        pull.assert_called_once()
        self.assertTrue(status.ok)

    def test_on_macos_the_app_is_launched_in_the_background(self):
        popen = mock.Mock()
        with mock.patch.object(oe.sys, "platform", "darwin"), \
                mock.patch.object(Path, "exists", return_value=True):
            how = oe.start_server(popen)
        self.assertEqual(how, "the Ollama app")
        self.assertEqual(popen.call_args.args[0], ["open", "-g", "-a", "Ollama"])

    def test_without_the_app_the_binary_is_served_detached(self):
        popen = mock.Mock()
        with mock.patch.object(oe.sys, "platform", "linux"), \
                mock.patch.object(oe.shutil, "which", return_value="/usr/bin/ollama"):
            how = oe.start_server(popen)
        self.assertIn("serve", how)
        self.assertEqual(popen.call_args.args[0], ["/usr/bin/ollama", "serve"])
        self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_the_embedding_model_is_the_hub_default_with_an_explicit_tag(self):
        self.assertEqual(oe.EMBED_MODEL, "mxbai-embed-large:latest")


class IdleTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        for target, value in (("STATE_FILE", out / "state.json"), ("LOCK_FILE", out / "lock"),
                              ("LOG_FILE", out / "log"), ("OUT", out)):
            patcher = mock.patch.object(idle, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def popen(self):
        return mock.patch.object(idle.subprocess, "Popen")

    def test_fresh_means_no_rebuild_and_no_ollama(self):
        with mock.patch.object(idle, "semantic_status", return_value=("fresh", "ok")), \
                mock.patch.object(oe, "ensure") as ensure, self.popen() as popen:
            message = idle.maybe_start()
        self.assertIn("fresh", message)
        ensure.assert_not_called()
        popen.assert_not_called()

    def test_stale_and_idle_starts_a_niced_detached_rebuild(self):
        with mock.patch.object(idle, "semantic_status", return_value=("stale", "3 changed")), \
                mock.patch.object(idle, "is_idle", return_value=True), \
                mock.patch.object(oe, "ensure", return_value=oe.Status(True, True, False, True, "ready")), \
                self.popen() as popen:
            message = idle.maybe_start()
        argv = popen.call_args.args[0]
        self.assertEqual(argv[:3], ["nice", "-n", "19"])
        self.assertIn("--run-build", argv)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertIn("rebuilding in the background", message)

    def test_a_busy_machine_does_not_start_anything(self):
        with mock.patch.object(idle, "semantic_status", return_value=("missing", "none")), \
                mock.patch.object(idle, "is_idle", return_value=False), \
                mock.patch.object(oe, "ensure") as ensure, self.popen() as popen:
            message = idle.maybe_start()
        self.assertIn("busy", message)
        ensure.assert_not_called()
        popen.assert_not_called()

    def test_a_held_lock_means_a_rebuild_is_already_running(self):
        with mock.patch.object(idle, "semantic_status", return_value=("stale", "x")), \
                mock.patch.object(idle, "is_idle", return_value=True), \
                mock.patch.object(idle, "lock_free", return_value=False), self.popen() as popen:
            message = idle.maybe_start()
        self.assertIn("already running", message)
        popen.assert_not_called()

    def test_the_real_lock_is_exclusive(self):
        import fcntl
        import os
        fd = os.open(idle.LOCK_FILE, os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            self.assertFalse(idle.lock_free())
        finally:
            os.close(fd)
        self.assertTrue(idle.lock_free())

    def test_a_missing_model_is_never_downloaded_by_the_idle_job(self):
        status = oe.Status(False, True, False, False, "model not installed")
        with mock.patch.object(idle, "semantic_status", return_value=("missing", "none")), \
                mock.patch.object(idle, "is_idle", return_value=True), \
                mock.patch.object(oe, "ensure", return_value=status) as ensure, self.popen() as popen:
            message = idle.maybe_start()
        self.assertNotIn("pull", ensure.call_args.kwargs)
        popen.assert_not_called()
        self.assertIn("not rebuilding", message)

    def test_a_second_check_inside_the_interval_is_throttled(self):
        with mock.patch.object(idle, "semantic_status", return_value=("fresh", "ok")) as status:
            idle.maybe_start(now=1000.0)
            idle.maybe_start(now=1000.0 + idle.MIN_INTERVAL - 1)
        self.assertEqual(status.call_count, 1)
        with mock.patch.object(idle, "semantic_status", return_value=("fresh", "ok")) as status:
            idle.maybe_start(now=1000.0 + idle.MIN_INTERVAL + 1)
        self.assertEqual(status.call_count, 1)

    def test_the_kill_switch_disables_automatic_starts_but_not_force(self):
        with mock.patch.dict(idle.os.environ, {"INDEX_NO_AUTO": "1"}), \
                mock.patch.object(idle, "semantic_status") as status:
            self.assertIn("disabled", idle.maybe_start())
        status.assert_not_called()

    def test_idle_means_load_below_the_threshold(self):
        with mock.patch.object(idle.os, "getloadavg", return_value=(1.0, 1.0, 1.0)):
            self.assertTrue(idle.is_idle(2.0))
        with mock.patch.object(idle.os, "getloadavg", return_value=(3.0, 1.0, 1.0)):
            self.assertFalse(idle.is_idle(2.0))

    def test_status_is_missing_without_an_index_and_stale_when_a_hash_differs(self):
        with mock.patch.object(idle, "active_manifest", return_value=None):
            self.assertEqual(idle.semantic_status()[0], "missing")
        manifest = Path(idle.OUT) / "m.json"
        manifest.write_text(json.dumps({"model": oe.EMBED_MODEL,
                                        "sourceSha1": {"README.md": "0" * 40}}))
        with mock.patch.object(idle, "active_manifest", return_value=(manifest, manifest)), \
                mock.patch.object(idle.build, "tracked_files", return_value=["README.md"]):
            self.assertEqual(idle.semantic_status()[0], "stale")

    def test_a_different_model_in_the_manifest_is_stale(self):
        manifest = Path(idle.OUT) / "m.json"
        manifest.write_text(json.dumps({"model": "nomic-embed-text", "sourceSha1": {}}))
        with mock.patch.object(idle, "active_manifest", return_value=(manifest, manifest)):
            status, why = idle.semantic_status()
        self.assertEqual(status, "stale")
        self.assertIn("nomic-embed-text", why)

    def test_the_idle_job_writes_only_gitignored_files(self):
        gitignore = (REPO / ".gitignore").read_text()
        for name in ("semantic-local.npz", "semantic-local.json", ".idle-state.json",
                     ".idle.lock", ".idle-index.log"):
            self.assertIn(f"index/{name}", gitignore)


class QueryTests(unittest.TestCase):
    def setUp(self):
        search.unload(model=False)
        self.addCleanup(lambda: search.unload(model=False))

    def test_keyword_mode_never_touches_ollama_and_prints_nothing(self):
        with mock.patch.object(oe, "ensure") as ensure, mock.patch("builtins.print") as printed:
            result = search.run_query("slippage fee", "keyword", 5, auto_index=False)
        ensure.assert_not_called()
        printed.assert_not_called()
        self.assertEqual(result.mode_used, "keyword")
        self.assertTrue(result.hits)
        self.assertLessEqual(len(result.hits), 5)

    def test_hybrid_falls_back_to_keyword_with_the_reason_when_ollama_is_down(self):
        down = oe.Status(False, False, False, None, "ollama is not reachable")
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "m.json"
            manifest.write_text(json.dumps({"model": oe.EMBED_MODEL}))
            with mock.patch.object(oe, "ensure", return_value=down), \
                    mock.patch.object(search, "semantic_pair", return_value=(manifest, manifest)), \
                    mock.patch("builtins.print") as printed:
                result = search.run_query("slippage", "hybrid", 3, auto_index=False)
        printed.assert_not_called()
        self.assertEqual(result.mode_used, "keyword")
        self.assertTrue(result.hits)
        self.assertTrue(any("not reachable" in n for n in result.notes))

    def test_semantic_only_with_no_index_returns_nothing_and_says_so(self):
        with mock.patch.object(search, "semantic_pair", return_value=None):
            result = search.run_query("slippage", "semantic", 3, auto_index=False)
        self.assertEqual(result.hits, [])
        self.assertTrue(result.notes)

    def test_the_kind_filter_applies(self):
        result = search.run_query("engine", "keyword", 10, kind="test", auto_index=False)
        self.assertTrue(result.hits)
        self.assertTrue(all(h.kind == "test" for h in result.hits))

    def test_unknown_mode_is_refused(self):
        with self.assertRaises(ValueError):
            search.run_query("x", "fuzzy", auto_index=False)

    def test_the_auto_index_note_is_included_when_enabled(self):
        with mock.patch.object(idle, "maybe_start", return_value="semantic index is fresh"):
            result = search.run_query("fee", "keyword", 1)
        self.assertIn("semantic index is fresh", result.notes)

    def test_nothing_is_cached_until_the_first_query_and_unload_empties_it(self):
        self.assertEqual(search._CACHE, {})
        search.run_query("fee", "keyword", 1, auto_index=False)
        self.assertTrue(search._CACHE)
        search.unload(model=False)
        self.assertEqual(search._CACHE, {})

    def test_unload_does_not_start_a_server(self):
        with mock.patch.object(oe, "reachable", return_value=False), \
                mock.patch.object(oe, "ensure") as ensure:
            message = search.unload()
        ensure.assert_not_called()
        self.assertIn("not running", message)

    def test_the_local_pair_wins_over_the_committed_pair(self):
        existing = {search.LOCAL_MANIFEST, search.LOCAL_NPZ, search.SEMANTIC_MANIFEST, search.SEMANTIC_NPZ}
        with mock.patch.object(Path, "exists", lambda self: self in existing):
            self.assertEqual(search.semantic_pair(), (search.LOCAL_MANIFEST, search.LOCAL_NPZ))
        existing -= {search.LOCAL_NPZ}
        with mock.patch.object(Path, "exists", lambda self: self in existing):
            self.assertEqual(search.semantic_pair(), (search.SEMANTIC_MANIFEST, search.SEMANTIC_NPZ))


if __name__ == "__main__":
    unittest.main()

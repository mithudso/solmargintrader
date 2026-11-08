"""Docs-tab index search: the `docs.search` commands and the lazy loading around them.

The memory claim is the point: the keyword postings, the embedding matrix and the ~670 MB
embedding model must not be loaded until someone searches, and must be releasable. Ollama and
the idle indexer are patched out; nothing here embeds anything or starts a process.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

from textual.widgets import DataTable, Input, Select, Static, TabbedContent

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "index"))

import idle  # noqa: E402
import ollama_ensure as oe  # noqa: E402

from soltui.commands import dispatch  # noqa: E402
from soltui.tests.bridge_support import World  # noqa: E402
from soltui.tests.test_tui import TEST_SIZE, make_settings, text_of  # noqa: E402
from soltui.tui import SolTuiApp  # noqa: E402


def forget_search() -> None:
    module = sys.modules.pop("repo_index_search", None)
    if module is not None:
        module.unload(model=False)


class DocsSearchCommands(unittest.TestCase):
    def setUp(self) -> None:
        forget_search()
        self.addCleanup(forget_search)
        self.world = World().__enter__()
        self.addCleanup(self.world.__exit__, None, None, None)
        patcher = mock.patch.object(idle, "maybe_start", return_value="semantic index is fresh")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_nothing_is_loaded_until_the_first_search(self) -> None:
        dispatch("docs.list", {"limit": 5})
        self.assertNotIn("repo_index_search", sys.modules)
        env = dispatch("docs.search", {"query": "slippage fee", "mode": "keyword"})
        self.assertTrue(env["ok"], env)
        self.assertIn("repo_index_search", sys.modules)

    def test_keyword_search_returns_catalogued_files_with_scores_and_never_calls_ollama(self) -> None:
        with mock.patch.object(oe, "ensure") as ensure:
            env = dispatch("docs.search", {"query": "slippage fee", "mode": "keyword", "limit": 5})
        ensure.assert_not_called()
        result = env["result"]
        self.assertEqual(result["mode_used"], "keyword")
        self.assertTrue(0 < len(result["hits"]) <= 5)
        hit = result["hits"][0]
        self.assertEqual(set(hit), {"path", "kind", "lines", "summary", "score", "editable"})
        self.assertTrue((REPO / hit["path"]).exists())

    def test_semantic_with_ollama_down_degrades_to_a_reason_not_a_crash(self) -> None:
        down = oe.Status(False, False, False, None, "ollama is not reachable")
        forget_search()
        with mock.patch.object(oe, "ensure", return_value=down):
            env = dispatch("docs.search", {"query": "slippage", "mode": "hybrid"})
        self.assertTrue(env["ok"], env)
        self.assertEqual(env["result"]["mode_used"], "keyword")
        self.assertTrue(env["result"]["hits"])

    def test_bad_requests_are_refused(self) -> None:
        self.assertEqual(dispatch("docs.search", {"query": "  "})["error"]["code"], "bad_params")
        self.assertEqual(dispatch("docs.search", {"query": "x", "mode": "fuzzy"})["error"]["code"], "bad_params")
        self.assertEqual(dispatch("docs.search", {"query": "x", "limit": "many"})["error"]["code"], "bad_params")

    def test_the_kind_filter_reaches_the_search(self) -> None:
        env = dispatch("docs.search", {"query": "engine", "mode": "keyword", "kind": "test"})
        self.assertTrue(env["result"]["hits"])
        self.assertTrue(all(h["kind"] == "test" for h in env["result"]["hits"]))

    def test_unload_before_any_search_says_there_is_nothing_to_free(self) -> None:
        env = dispatch("docs.search_unload", {})
        self.assertIn("never loaded", env["result"]["message"])

    def test_unload_after_a_search_empties_the_cache_and_leaves_ollama_alone_if_it_is_down(self) -> None:
        dispatch("docs.search", {"query": "fee", "mode": "keyword"})
        module = sys.modules["repo_index_search"]
        self.assertTrue(module._CACHE)
        with mock.patch.object(oe, "reachable", return_value=False), mock.patch.object(oe, "ensure") as ensure:
            env = dispatch("docs.search_unload", {})
        ensure.assert_not_called()
        self.assertEqual(module._CACHE, {})
        self.assertIn("not running", env["result"]["message"])


class DocsSearchTab(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        forget_search()
        self.addCleanup(forget_search)
        patcher = mock.patch.object(idle, "maybe_start", return_value="semantic index is fresh")
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_search_fills_the_table_and_the_tab_loads_nothing_before_it(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            self.assertNotIn("repo_index_search", sys.modules, "opening the tab must not load search")
            app.query_one("#docs-search-mode", Select).value = "keyword"
            box = app.query_one("#docs-search", Input)
            box.value = "slippage fee"
            await pilot.click("#docs-search-run")
            for _ in range(40):
                await pilot.pause(0.25)
                if "hits" in text_of(app, "#docs-search-status"):
                    break
            table = app.query_one("#docs-table", DataTable)
            self.assertGreater(table.row_count, 0)
            self.assertIn("keyword", text_of(app, "#docs-search-status"))
            self.assertIn("search results", text_of(app, "#docs-headline"))
            first = str(table.get_row_at(0)[4])
            self.assertRegex(first, r"^\d+\.\d{3}  ")

    async def test_an_empty_box_restores_the_plain_file_list(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            await pilot.click("#docs-search-run")
            await pilot.pause()
            self.assertIn("file list", text_of(app, "#docs-search-status"))
            self.assertGreater(app.query_one("#docs-table", DataTable).row_count, 20)

    async def test_free_search_memory_reports(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            await pilot.click("#docs-search-free")
            await pilot.pause()
            self.assertIn("never loaded", text_of(app, "#docs-search-status"))


if __name__ == "__main__":
    unittest.main()

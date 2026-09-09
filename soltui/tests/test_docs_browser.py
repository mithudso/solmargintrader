"""Tests for the Docs tab's editing guards.

The load-bearing assertions are the refusals: a file under `research/results/`
or not in the catalogue must never be writable, regardless of what the caller
claims about it. Those are the properties a UI bug could silently violate, so
they are asserted directly rather than left to code review.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from soltui import docs_browser


def _entry(path: str, kind: str = "code-python", size: int = 100) -> docs_browser.DocEntry:
    return docs_browser.DocEntry(
        path=path, name=Path(path).name, directory=str(Path(path).parent),
        kind=kind, summary="", summary_source="none", lines=10, size=size,
    )


class IsEditableTests(unittest.TestCase):
    """Metadata-only, so none of these touch the filesystem."""

    def test_ordinary_source_file_is_editable(self) -> None:
        self.assertTrue(docs_browser.is_editable(_entry("soltui/app.py")))

    def test_results_prefix_is_never_editable(self) -> None:
        entry = _entry("research/results/sweep.csv", kind="code-python")
        self.assertFalse(docs_browser.is_editable(entry))

    def test_result_kind_is_never_editable(self) -> None:
        # Belt-and-braces: classify() tags anything under a "results" dir as
        # kind="result" even outside research/results/ specifically.
        entry = _entry("backtester/results/x.csv", kind="result")
        self.assertFalse(docs_browser.is_editable(entry))

    def test_other_kind_is_not_editable(self) -> None:
        # Binaries and unclassified files (icons, etc.) fall to kind="other".
        entry = _entry("soltui/SolTUI.icns", kind="other")
        self.assertFalse(docs_browser.is_editable(entry))

    def test_oversized_file_is_not_editable(self) -> None:
        entry = _entry("docs/BIG.md", size=docs_browser.MAX_VIEW_BYTES + 1)
        self.assertFalse(docs_browser.is_editable(entry))


class WriteDocumentTests(unittest.TestCase):
    """`write_document` re-derives every guard; these check it actually does."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        (self.repo / "soltui").mkdir()
        (self.repo / "research" / "results").mkdir(parents=True)
        self._patch = mock.patch.object(docs_browser, "REPO", self.repo)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_writes_and_round_trips_through_read_document(self) -> None:
        target = self.repo / "soltui" / "app.py"
        target.write_text("old\n", encoding="utf-8")
        entries = [_entry("soltui/app.py")]

        written = docs_browser.write_document("soltui/app.py", "new\n", entries)

        self.assertEqual(written, target.resolve())
        self.assertEqual(target.read_text(encoding="utf-8"), "new\n")
        text, _language, is_real_text = docs_browser.read_document(
            "soltui/app.py", entries)
        self.assertEqual(text, "new\n")
        self.assertTrue(is_real_text)

    def test_refuses_path_not_in_catalogue(self) -> None:
        with self.assertRaises(PermissionError):
            docs_browser.write_document("soltui/app.py", "x", entries=[])

    def test_refuses_results_prefix_even_if_kind_lies(self) -> None:
        entries = [_entry("research/results/sweep.csv", kind="code-python")]
        target = self.repo / "research" / "results" / "sweep.csv"
        target.write_text("original\n", encoding="utf-8")

        with self.assertRaises(PermissionError):
            docs_browser.write_document(
                "research/results/sweep.csv", "tampered\n", entries)
        self.assertEqual(target.read_text(encoding="utf-8"), "original\n")

    def test_refuses_when_entry_kind_is_result(self) -> None:
        entries = [_entry("backtester/results/x.csv", kind="result")]
        with self.assertRaises(PermissionError):
            docs_browser.write_document("backtester/results/x.csv", "x", entries)

    def test_refuses_entry_whose_path_resolves_outside_repo(self) -> None:
        # is_editable() is metadata-only and would say yes; resolve()'s
        # is_relative_to(REPO) check is the guard that must actually stop
        # this, so it needs its own test rather than riding along on one of
        # the cases above.
        entries = [_entry("../outside.py")]
        with self.assertRaises(FileNotFoundError):
            docs_browser.write_document("../outside.py", "x", entries)


class ReadDocumentRealTextFlagTests(unittest.TestCase):
    """`read_document`'s third element is what gates the Save button in the
    UI, so its two False branches need direct coverage, not just the True
    path exercised by the round-trip test above."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        self._patch = mock.patch.object(docs_browser, "REPO", self.repo)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_oversized_file_reports_not_real_text(self) -> None:
        target = self.repo / "big.md"
        target.write_bytes(b"x" * (docs_browser.MAX_VIEW_BYTES + 1))
        entries = [_entry("big.md")]

        text, language, is_real_text = docs_browser.read_document("big.md", entries)

        self.assertFalse(is_real_text)
        self.assertEqual(language, "")
        self.assertIn("above", text)

    def test_non_utf8_file_reports_not_real_text(self) -> None:
        target = self.repo / "binary.py"
        target.write_bytes(b"\xff\xfe\x00\x01")
        entries = [_entry("binary.py")]

        text, language, is_real_text = docs_browser.read_document(
            "binary.py", entries)

        self.assertFalse(is_real_text)
        self.assertEqual(language, "")
        self.assertIn("not UTF-8", text)


if __name__ == "__main__":
    unittest.main()

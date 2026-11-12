"""Behavior checks for offline HTML conversion and safe recursive output."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.html_to_markdown import conversion_plan, html_to_markdown, main, read_html


class MarkdownTests(unittest.TestCase):
    def test_layout_wrappers_do_not_break_heading_or_list_markers(self) -> None:
        text = html_to_markdown(
            "<h2> <div>Hello,</div><div>Trader</div></h2>"
            "<ul><li><p>First</p><div>item</div></li></ul>"
        )
        self.assertIn("## Hello, Trader", text)
        self.assertIn("- First item", text)

    def test_structure_and_text_only_links(self) -> None:
        text = html_to_markdown(
            "<h1>Title</h1><p>Hello <b>world</b> &amp; friends.</p>"
            "<ul><li>First<ul><li>Nested</li></ul></li><li>Last</li></ul>"
            '<ol start="3"><li>Third</li><li>Fourth</li></ol>'
            '<p><a href="https://example.com">Label</a><img src="pic.png"></p>'
            "<table><tr><th>Name</th><th>Value</th></tr>"
            "<tr><td>Alpha</td><td>42</td></tr></table>"
        )
        for expected in (
            "# Title",
            "Hello world &amp; friends.",
            "- First",
            "    - Nested",
            "- Last",
            "3. Third",
            "4. Fourth",
            "Label",
            "Name | Value",
            "Alpha | 42",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("https://", text)
        self.assertNotIn("pic.png", text)

    def test_embedded_and_hidden_payloads_are_removed(self) -> None:
        text = html_to_markdown(
            "<head><title>SECRET</title></head><script>SECRET</script>"
            "<style>SECRET</style><svg><text>SECRET</text></svg>"
            "<div hidden><span>SECRET</span><p>SECRET</p></div>"
            '<p aria-hidden="true">SECRET</p><div style="display: none">SECRET</div>'
            '<img hidden src="SECRET"><p>visible</p><!-- SECRET -->'
        )
        self.assertEqual(text, "visible\n")

    def test_code_keeps_indentation_blank_lines_and_literal_markup(self) -> None:
        text = html_to_markdown(
            '<pre><code>if x &lt; 2:\n    print("a")\n\n\n    ```\n</code></pre>'
            "<p>&lt;script&gt;literal&lt;/script&gt;</p>"
        )
        self.assertIn('````\nif x < 2:\n    print("a")\n\n\n    ```\n````', text)
        self.assertIn("&lt;script&gt;literal&lt;/script&gt;", text)

    def test_unclosed_pre_and_stray_endtag(self) -> None:
        self.assertEqual(html_to_markdown("<pre>a\n  b"), "```\na\n  b\n```\n")
        self.assertEqual(html_to_markdown("<div hidden>bad</other>bad</div>ok"), "ok\n")


class FileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source"
        self.source.mkdir()
        self.output = Path(self.temp.name) / "output"

    def run_converter(self, *extra: str) -> int:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return main([str(self.source), "--output", str(self.output), *extra])

    def test_recursion_case_insensitive_extensions_rerun_and_overwrite(self) -> None:
        (self.source / "nested").mkdir()
        page = self.source / "nested/page.HTML"
        page.write_text("<h2>Old</h2>")
        (self.source / "root.htm").write_text("<p>Root</p>")
        (self.source / "ignore.js").write_text("ignored")
        self.assertEqual(self.run_converter(), 0)
        self.assertEqual(len(list(self.output.rglob("*.md"))), 2)
        target = self.output / "nested/page.md"
        self.assertEqual(target.read_text(), "## Old\n")
        page.write_text("<h2>New</h2>")
        self.assertEqual(self.run_converter(), 0)
        self.assertEqual(target.read_text(), "## Old\n")
        self.assertEqual(self.run_converter("--overwrite"), 0)
        self.assertEqual(target.read_text(), "## New\n")
        self.assertEqual(list(self.output.rglob(".html-md-*")), [])

    def test_collisions_abort_before_writing(self) -> None:
        (self.source / "page.html").write_text("a")
        (self.source / "page.htm").write_text("b")
        with self.assertRaisesRegex(ValueError, "collision"):
            conversion_plan(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_dry_run_and_nested_output_exclusion(self) -> None:
        (self.source / "page.html").write_text("<p>yes</p>")
        self.assertEqual(self.run_converter("--dry-run"), 0)
        self.assertFalse(self.output.exists())
        self.output = self.source / "markdown"
        self.output.mkdir()
        (self.output / "unrelated.html").write_text("ignore")
        self.assertEqual(len(conversion_plan(self.source, self.output)), 1)

    def test_source_symlinks_are_not_followed(self) -> None:
        (self.source / "page.html").write_text("<p>yes</p>")
        (self.source / "alias.html").symlink_to(self.source / "page.html")
        (self.source / "cycle").symlink_to(self.source, target_is_directory=True)
        self.assertEqual(len(conversion_plan(self.source, self.output)), 1)

    def test_output_ancestor_symlinks_are_refused_before_any_write(self) -> None:
        nested = self.source / "nested"
        nested.mkdir()
        (nested / "page.html").write_text("<p>public fixture</p>")
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        self.output.mkdir()
        (self.output / "nested").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            conversion_plan(self.source, self.output)
        self.assertEqual(list(outside.iterdir()), [])

    def test_invalid_encoding_reports_failure_and_continues(self) -> None:
        (self.source / "bad.html").write_bytes(b'<meta charset="not-real"><p>bad</p>')
        (self.source / "good.html").write_text("<p>ok</p>")
        self.assertEqual(self.run_converter(), 1)
        self.assertEqual((self.output / "good.md").read_text(), "ok\n")
        self.assertFalse((self.output / "bad.md").exists())

    def test_bom_declared_and_fallback_encodings(self) -> None:
        path = self.source / "page.html"
        for raw in (
            "<p>café</p>".encode("utf-8-sig"),
            "<p>café</p>".encode("utf-16"),
            b'<meta charset="windows-1252"><p>caf\xe9</p>',
            b"<p>caf\xe9</p>",
        ):
            path.write_bytes(raw)
            self.assertIn("café", read_html(path))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from website.scripts import build_paper
from website.scripts.build_paper import PaperError

SOURCE = "research/papers/EXAMPLE.md"
SLUGS = {"research/papers/OTHER.md": "other-12345678", "research/json/run/report.md": "report-abcdef01",
         "research/papers/two words.md": "two-words-00000001"}
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'


def body(markdown: str, figures: list[dict] | None = None, pdf_route: str = "/papers/example.pdf") -> str:
    return build_paper.render_body(markdown, source=SOURCE, slugs=SLUGS, pdf_route=pdf_route,
                                   figures=figures or [])[1]


class RenderBodyTest(unittest.TestCase):
    def test_title_comes_from_the_first_heading_without_markup(self):
        title, html = build_paper.render_body("# A `coded` *title*\n\nLead.\n", source=SOURCE, slugs=SLUGS,
                                              pdf_route="/papers/example.pdf", figures=[])
        self.assertEqual(title, "A coded title")
        self.assertIn("<h1>A <code>coded</code> <em>title</em></h1>", html)

    def test_a_paper_without_a_title_is_refused(self):
        with self.assertRaisesRegex(PaperError, "title"):
            body("Only a paragraph.\n")

    def test_wrapped_lines_join_into_one_paragraph_and_only_the_first_is_the_lead(self):
        html = body("# T\n\nFirst line\nsecond line.\n\nNext paragraph.\n")
        self.assertIn('<p class="lead">First line second line.</p>', html)
        self.assertIn("<p>Next paragraph.</p>", html)

    def test_metadata_lines_keep_their_line_breaks(self):
        html = body("# T\n\nLead.\n\nVersion: 1.0.0\nDate: 2026-11-27\nAuthor: A\nStatus: Working paper.\n")
        self.assertIn('<p class="meta">Version: 1.0.0<br>Date: 2026-11-27<br>Author: A<br>Status: Working paper.</p>',
                      html)

    def test_a_paragraph_that_only_starts_like_metadata_stays_a_paragraph(self):
        html = body("# T\n\nLead.\n\nStatus: draft\nand then prose follows.\n")
        self.assertNotIn('class="meta"', html)

    def test_the_link_to_the_papers_own_pdf_is_left_out(self):
        html = body("# T\n\nLead.\n\n[Download the paper as PDF](https://oraclebot.io/papers/example.pdf)\n")
        self.assertNotIn("Download", html)

    def test_a_link_to_another_pdf_is_kept(self):
        html = body("# T\n\nLead.\n\n[Earlier paper](https://oraclebot.io/papers/earlier.pdf)\n")
        self.assertIn('<a href="https://oraclebot.io/papers/earlier.pdf">Earlier paper</a>', html)

    def test_relative_links_resolve_through_the_catalogue(self):
        html = body("# T\n\nSee [the study](OTHER.md), [the report](../json/run/report.md) and "
                    "[a spaced name](two%20words.md).\n")
        self.assertIn('<a href="https://oraclebot.io/#research/other-12345678">the study</a>', html)
        self.assertIn('<a href="https://oraclebot.io/#research/report-abcdef01">the report</a>', html)
        self.assertIn('<a href="https://oraclebot.io/#research/two-words-00000001">a spaced name</a>', html)

    def test_links_the_library_reader_drops_print_as_text(self):
        # app.js refuses a relative link that carries a fragment, a query or a backslash.
        html = body("# T\n\nSee [a](OTHER.md#part), [b](OTHER.md?x=1) and [c](..\\papers\\OTHER.md).\n")
        self.assertNotIn("<a ", html)
        self.assertIn("See a, b and c.", html)

    def test_links_the_catalogue_cannot_place_print_as_text(self):
        html = body("# T\n\nSee [the data](data.csv), [a script](javascript:alert(1)) and [home](/).\n")
        self.assertNotIn("<a ", html)
        self.assertIn("See the data, a script", html)

    def test_text_is_escaped(self):
        html = body("# T\n\nRSI < 30 & `a<b` and **x>y**.\n")
        self.assertIn("RSI &lt; 30 &amp; <code>a&lt;b</code> and <strong>x&gt;y</strong>.", html)

    def test_a_link_address_cannot_break_out_of_its_attribute(self):
        html = body('# T\n\n[x](https://example.com/"onmouseover="alert(1))\n')
        self.assertNotIn('"onmouseover="', html)
        self.assertIn("&quot;onmouseover=&quot;", html)

    def test_a_number_range_cannot_wrap_at_its_dash(self):
        html = body("# T\n\nThe zone is $95.34–98.00, not a list – of things.\n")
        self.assertIn("$95.34⁠–⁠98.00", html)
        self.assertIn("list – of", html)

    def test_lists_follow_their_first_marker_and_close_before_prose(self):
        html = body("# T\n\n- one\n- two\n\n1. first\n2. second\n\nAfter.\n")
        self.assertIn("<ul>\n<li>one</li>\n<li>two</li>\n</ul>", html)
        self.assertIn("<ol>\n<li>first</li>\n<li>second</li>\n</ol>", html)
        self.assertLess(html.index("</ol>"), html.index("After."))

    def test_a_line_wrapped_under_a_list_item_prints_after_the_list(self):
        html = body("# T\n\nLead.\n\n- one\n  wrapped tail\n- two\n\nAfter.\n")
        self.assertIn("<ul>\n<li>one</li>\n</ul>\n<p>  wrapped tail</p>\n<ul>\n<li>two</li>\n</ul>", html)

    def test_code_blocks_keep_their_text_exactly(self):
        html = body("# T\n\n```\npython -m x --flag <dir>\n**not bold**\n```\n")
        self.assertIn("<pre>python -m x --flag &lt;dir&gt;\n**not bold**</pre>", html)

    def test_tables_carry_alignment_and_escaped_pipes(self):
        html = body("# T\n\n| Name | Value | Mid |\n|---|---:|:-:|\n| a \\| b | +1.0% | x |\n\nAfter.\n")
        self.assertIn('<th scope="col">Name</th><th scope="col" style="text-align:right">Value</th>', html)
        self.assertIn('<td>a | b</td><td style="text-align:right">+1.0%</td><td style="text-align:center">x</td>',
                      html)
        self.assertIn('<table class="short">', html)

    def test_a_left_alignment_marker_is_kept(self):
        html = body("# T\n\n| A | B |\n|:--|--|\n| 1 | 2 |\n")
        self.assertIn('<th scope="col" style="text-align:left">A</th><th scope="col">B</th>', html)

    def test_a_long_table_may_break_across_pages(self):
        rows = "".join(f"| r{i} | {i} |\n" for i in range(build_paper.SHORT_TABLE_ROWS + 1))
        html = body("# T\n\n| A | B |\n|---|---|\n" + rows)
        self.assertIn("<table><thead>", html)

    def test_a_row_with_the_wrong_cell_count_ends_the_table(self):
        html = body("# T\n\n| A | B |\n|---|---|\n| 1 | 2 |\n| only one |\n")
        self.assertEqual(html.count("<tr>"), 2)
        self.assertIn("only one", html)

    def test_a_figure_follows_the_paragraph_that_names_it(self):
        figures = [{"after_text": "as Figure 1", "caption": "Figure 1. A *square*.", "markup": SVG}]
        html = body("# T\n\nLead.\n\nShown as Figure 1.\n\n| A |\n|---|\n| 1 |\n", figures)
        self.assertLess(html.index("Shown as Figure 1."), html.index("<figure>"))
        self.assertLess(html.index("</figure>"), html.index("<table"))
        self.assertIn("<figcaption>Figure 1. A <em>square</em>.</figcaption>", html)

    def test_a_figure_with_no_anchor_in_the_paper_is_refused(self):
        figures = [{"after_text": "as Figure 9", "caption": "c", "markup": SVG}]
        with self.assertRaisesRegex(PaperError, "Figure 9"):
            body("# T\n\nLead.\n", figures)


class RenderHtmlTest(unittest.TestCase):
    def test_the_footer_and_title_reach_the_page(self):
        html = build_paper.render_html("# A & B\n\nLead.\n", source=SOURCE, slugs=SLUGS,
                                       pdf_route="/papers/example.pdf", footer="Oraclebot Research · Working paper",
                                       figures=[])
        self.assertIn("<title>A &amp; B · Oraclebot Research</title>", html)
        self.assertIn('content: "Oraclebot Research · Working paper · " counter(page)', html)

    def test_a_footer_that_would_end_the_css_string_is_refused(self):
        with self.assertRaisesRegex(PaperError, "footer"):
            build_paper.render_html("# T\n\nLead.\n", source=SOURCE, slugs=SLUGS, pdf_route="/papers/example.pdf",
                                    footer='x"; } body { display: none', figures=[])


class BuildFileTest(unittest.TestCase):
    def setUp(self):
        # A throwaway repository root, so the tests never write into the real tree.
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        patched = mock.patch.object(build_paper, "ROOT", self.root)
        patched.start()
        self.addCleanup(patched.stop)
        self.work = self.root / "research/json/run"
        self.work.mkdir(parents=True)
        (self.work / "paper.md").write_text("# T\n\nLead as Figure 1.\n", encoding="utf-8")
        (self.work / "figure.svg").write_text(SVG, encoding="utf-8")

    def write(self, **changes) -> Path:
        relative = self.work.relative_to(self.root).as_posix()
        build = {"source": f"{relative}/paper.md", "output": "website/public/papers/example.pdf", "footer": "F",
                 "figures": [{"after_text": "as Figure 1", "svg": "figure.svg", "caption": "c"}]} | changes
        path = self.work / "paper.json"
        path.write_text(json.dumps(build), encoding="utf-8")
        return path

    def test_a_build_file_loads_its_paper_and_figures(self):
        build = build_paper.load_build(self.write())
        self.assertEqual(build["pdf_route"], "/papers/example.pdf")
        self.assertEqual(build["figures"][0]["markup"], SVG)
        self.assertTrue(build["markdown"].startswith("# T"))

    def test_an_output_outside_the_public_site_is_refused(self):
        for output in ("website/scripts/example.pdf", "../outside.pdf", "website/public/papers/example.html"):
            with self.subTest(output=output), self.assertRaises(PaperError):
                build_paper.load_build(self.write(output=output))

    def test_a_source_outside_the_repository_is_refused(self):
        with self.assertRaisesRegex(PaperError, "outside"):
            build_paper.load_build(self.write(source="../../etc/hosts"))

    def test_a_missing_field_is_named(self):
        path = self.write()
        path.write_text(json.dumps({"source": "x.md"}), encoding="utf-8")
        with self.assertRaisesRegex(PaperError, "output, footer"):
            build_paper.load_build(path)

    def test_a_build_file_kept_outside_the_repository_is_refused_cleanly(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            (Path(elsewhere) / "figure.svg").write_text(SVG, encoding="utf-8")
            path = Path(elsewhere) / "paper.json"
            path.write_text(self.write().read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaisesRegex(PaperError, "figure is outside"):
                build_paper.load_build(path)

    def test_a_malformed_build_file_is_named_not_a_traceback(self):
        for changes, message in (({"figures": [{"svg": "figure.svg"}]}, "figure 1 needs"),
                                 ({"figures": "figure.svg"}, "must be a list")):
            with self.subTest(message=message), self.assertRaisesRegex(PaperError, message):
                build_paper.load_build(self.write(**changes))
        path = self.write()
        path.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(PaperError, "JSON object"):
            build_paper.load_build(path)

    def test_a_figure_with_a_script_or_an_outside_reference_is_refused(self):
        for markup in (SVG.replace("<rect", "<script>1</script><rect"),
                       SVG.replace("<rect", '<rect onload="x()"'),
                       SVG.replace("<rect", '<image href="https://example.com/a.png"/><rect'),
                       "<p>not a drawing</p>"):
            (self.work / "figure.svg").write_text(markup, encoding="utf-8")
            with self.subTest(markup=markup[:60]), self.assertRaises(PaperError):
                build_paper.load_build(self.write())

    def test_main_reports_a_bad_build_file_and_writes_nothing(self):
        path = self.write(output="../outside.pdf")
        with mock.patch("sys.stderr") as stderr:
            self.assertEqual(build_paper.main([str(path)]), 1)
        self.assertIn("outside", "".join(call.args[0] for call in stderr.write.call_args_list))

    def test_main_prints_the_pdf_and_reports_its_size(self):
        def write_pdf(html: str, output: Path) -> None:
            self.assertIn("<figure>", html)
            output.parent.mkdir(parents=True)
            output.write_bytes(b"%PDF")

        stdout = io.StringIO()
        with mock.patch.object(build_paper, "print_pdf", side_effect=write_pdf), contextlib.redirect_stdout(stdout):
            self.assertEqual(build_paper.main([str(self.write())]), 0)
        self.assertEqual(stdout.getvalue().strip(), "Wrote website/public/papers/example.pdf (4 bytes)")

    def test_html_only_build_does_not_need_a_browser(self):
        target = self.work / "paper.html"
        with mock.patch.object(build_paper, "find_chrome", side_effect=AssertionError("browser used")):
            self.assertEqual(build_paper.main([str(self.write()), "--html", str(target), "--no-pdf"]), 0)
        self.assertIn("<figure>", target.read_text(encoding="utf-8"))


class PrintPdfTest(unittest.TestCase):
    def test_a_failed_print_leaves_the_published_file_alone(self):
        with tempfile.TemporaryDirectory() as work:
            output = Path(work) / "paper.pdf"
            output.write_bytes(b"published")
            failed = mock.Mock(returncode=1, stderr="boom")
            with mock.patch.object(build_paper, "find_chrome", return_value="chrome"), \
                    mock.patch.object(build_paper.subprocess, "run", return_value=failed), \
                    self.assertRaisesRegex(PaperError, "exit 1"):
                build_paper.print_pdf("<html></html>", output)
            self.assertEqual(output.read_bytes(), b"published")

    def test_a_successful_print_replaces_the_published_file(self):
        def chrome(command, **_):
            target = next(arg for arg in command if arg.startswith("--print-to-pdf="))
            Path(target.split("=", 1)[1]).write_bytes(b"%PDF new")
            return mock.Mock(returncode=0, stderr="")

        with tempfile.TemporaryDirectory() as work:
            output = Path(work) / "papers" / "paper.pdf"
            with mock.patch.object(build_paper, "find_chrome", return_value="chrome"), \
                    mock.patch.object(build_paper.subprocess, "run", side_effect=chrome):
                build_paper.print_pdf("<html></html>", output)
            self.assertEqual(output.read_bytes(), b"%PDF new")

    def test_a_browser_that_never_finishes_or_writes_nothing_is_reported(self):
        for outcome, message in ((subprocess.TimeoutExpired("chrome", 1), "did not finish"),
                                 (mock.Mock(returncode=0, stderr=""), "did not write a PDF")):
            with tempfile.TemporaryDirectory() as work, self.subTest(message=message), \
                    mock.patch.object(build_paper, "find_chrome", return_value="chrome"), \
                    mock.patch.object(build_paper.subprocess, "run", side_effect=[outcome]), \
                    self.assertRaisesRegex(PaperError, message):
                build_paper.print_pdf("<html></html>", Path(work) / "paper.pdf")

    def test_the_browser_named_by_chrome_is_used_or_refused_never_replaced(self):
        with mock.patch.object(build_paper, "CHROME_CANDIDATES", (sys.executable,)):
            with mock.patch.dict(build_paper.os.environ, {"CHROME": sys.executable}):
                self.assertEqual(build_paper.find_chrome(), sys.executable)
            with mock.patch.dict(build_paper.os.environ, {"CHROME": "/no/such/browser"}), \
                    self.assertRaisesRegex(PaperError, "CHROME does not name"):
                build_paper.find_chrome()

    def test_no_browser_is_reported_by_name(self):
        with mock.patch.dict(build_paper.os.environ, {"CHROME": ""}), \
                mock.patch.object(build_paper, "CHROME_CANDIDATES", ("no-such-browser",)), \
                mock.patch.object(build_paper.shutil, "which", return_value=None), \
                self.assertRaisesRegex(PaperError, "CHROME"):
            build_paper.find_chrome()


class PublishedPaperTest(unittest.TestCase):
    """Every committed build file must still render against the committed paper."""

    def test_each_build_file_renders(self):
        builds = sorted((build_paper.ROOT / "research/json").glob("*/paper.json"))
        self.assertTrue(builds)
        for path in builds:
            with self.subTest(build=path.parent.name):
                build = build_paper.load_build(path)
                html = build_paper.render_html(build["markdown"], source=build["source"],
                                               slugs=build_paper.catalog_slugs(), pdf_route=build["pdf_route"],
                                               footer=build["footer"], figures=build["figures"])
                self.assertEqual(html.count("<figure>"), len(build["figures"]))
                self.assertTrue(build["output"].is_file(), "the PDF named by the build file is not committed")


if __name__ == "__main__":
    unittest.main()

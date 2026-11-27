"""Build a working paper's PDF from its Markdown source.

The research library renders papers with the small Markdown reader in
``website/public/app.js``. This module reads the same subset the same way, so
the PDF and the library article cannot drift apart in structure, then prints the
result with headless Chrome. Figures exist only in the PDF, because the library
reader has no images; a paper's build file says where each one goes.

    python -m website.scripts.build_paper research/json/hype-paper-20261127/paper.json
    python -m website.scripts.build_paper <paper.json> --html /tmp/paper.html --no-pdf

Chrome stamps a creation time into every PDF, so the output is not byte-stable
and has no ``--check`` mode. Set ``CHROME`` to choose the browser binary.
"""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "https://oraclebot.io"
CATALOG = ROOT / "website/public/research/catalog.json"
CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)
CHROME_TIMEOUT_SECONDS = 120
FIGURE_KEYS = ("after_text", "svg", "caption")
INLINE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*")
METADATA_LINE = re.compile(r"^(Version|Date|Author|Status): \S")
NUMBER_RANGE = re.compile(r"(?<=\d)–(?=\d)")
SHORT_TABLE_ROWS = 5
SVG_ROOT = re.compile(r"<svg\b[^>]*>")
UNSAFE_SVG = re.compile(r"<\s*(script|foreignObject|iframe|image|use)\b|\son\w+\s*=|javascript:|\b(?:href|src)\s*=", re.IGNORECASE)

STYLE = """
@page { size: A4; margin: 19mm 18mm 21mm;
  @bottom-center { content: "%(footer)s · " counter(page) " / " counter(pages);
    font: 7.5pt Helvetica, Arial, sans-serif; color: #6e776d; } }
* { box-sizing: border-box; }
html { font: 10.2pt/1.5 Georgia, 'Times New Roman', serif; color: #222e29; }
body { margin: 0; }
h1, h2, h3, table, figcaption, .meta { font-family: Helvetica, Arial, sans-serif; }
h1 { font-size: 23pt; line-height: 1.15; margin: 0 0 12pt; color: #173f35; }
h2 { font-size: 13pt; margin: 20pt 0 6pt; color: #173f35; break-after: avoid; }
h3 { font-size: 10.5pt; margin: 14pt 0 4pt; color: #173f35; break-after: avoid; }
p { margin: 0 0 7pt; orphans: 3; widows: 3; }
.lead { font-size: 11.5pt; }
.meta { font-size: 8.4pt; line-height: 1.55; color: #6e776d; border-left: 2pt solid #d8ed9f;
  padding-left: 8pt; margin: 10pt 0 14pt; }
a { color: #173f35; text-decoration: underline; text-decoration-color: #b9c4b0; }
ul, ol { margin: 0 0 7pt; padding-left: 16pt; }
li { margin-bottom: 3pt; }
code { font: 8.6pt 'SFMono-Regular', Menlo, Consolas, monospace; }
pre { font: 7.8pt/1.45 'SFMono-Regular', Menlo, Consolas, monospace; background: #f1f4ea;
  border: 0.5pt solid #e1e5dc; border-radius: 3pt; padding: 6pt 8pt; margin: 0 0 8pt;
  white-space: pre-wrap; overflow-wrap: anywhere; break-inside: avoid; }
table { width: 100%%; border-collapse: collapse; font-size: 7.7pt; line-height: 1.35; margin: 4pt 0 10pt; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
table.short { break-inside: avoid; }
th { text-align: left; font-weight: 700; color: #173f35; border-bottom: 0.8pt solid #173f35;
  padding: 3pt 5pt 3pt 0; vertical-align: bottom; }
td { border-bottom: 0.4pt solid #e1e5dc; padding: 3pt 5pt 3pt 0; vertical-align: top;
  font-variant-numeric: tabular-nums; }
th:last-child, td:last-child { padding-right: 0; }
figure { margin: 8pt 0 12pt; break-inside: avoid; }
figure svg { display: block; width: 100%%; height: auto; }
figcaption { font-size: 8pt; color: #6e776d; margin-top: 4pt; }
hr { border: 0; border-top: 0.5pt solid #e1e5dc; margin: 12pt 0; }
"""


class PaperError(ValueError):
    """The build file or the paper cannot be turned into a PDF as written."""


def catalog_slugs(catalog_path: Path = CATALOG) -> dict[str, str]:
    """Map each published source path to its library slug."""
    articles = json.loads(catalog_path.read_text(encoding="utf-8"))["articles"]
    return {article["source"]: article["slug"] for article in articles}


def resolve_link(href: str, source: str, slugs: dict[str, str]) -> str | None:
    """Return an absolute address for ``href``, or ``None`` to print plain text.

    The library turns a relative link into its own article address and drops any
    link it cannot place, including one with a fragment, a query or a backslash
    (``articleHref`` in app.js). A PDF has no base address, so the same rule
    applies here with the public origin written in.
    """
    if re.match(r"^https?://", href, re.IGNORECASE):
        return href
    href = href.strip()
    if re.search(r"^(?:[a-z][a-z0-9+.-]*:|/)|[\\?#]", href, re.IGNORECASE):
        return None
    target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(href)))
    slug = slugs.get(target)
    return f"{ORIGIN}/#research/{slug}" if slug else None


def plain(text: str) -> str:
    """Escape running text, and keep a price or date range on one line.

    A range such as $95.34–98.00 that wraps after its dash reads as two prices.
    Word joiners around the dash stop the browser from breaking there.
    """
    return NUMBER_RANGE.sub("\u2060–\u2060", escape(text, quote=False))


def inline(text: str, source: str, slugs: dict[str, str]) -> str:
    parts, start = [], 0
    for match in INLINE.finditer(text):
        parts.append(plain(text[start:match.start()]))
        label, href, code, strong, emphasis = match.groups()
        if label is not None:
            address = resolve_link(href, source, slugs)
            parts.append(f'<a href="{escape(address)}">{plain(label)}</a>' if address else plain(label))
        elif code is not None:
            parts.append(f"<code>{escape(code, quote=False)}</code>")
        elif strong is not None:
            parts.append(f"<strong>{plain(strong)}</strong>")
        else:
            parts.append(f"<em>{plain(emphasis)}</em>")
        start = match.end()
    parts.append(plain(text[start:]))
    return "".join(parts)


def table_cells(line: str) -> list[str]:
    trimmed = line.strip()
    if "|" not in trimmed:
        return []
    trimmed = re.sub(r"^\|", "", trimmed)
    trimmed = re.sub(r"(?<!\\)\|$", "", trimmed)
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", trimmed)]


def alignment(marker: str) -> str:
    if marker.endswith(":"):
        return ' style="text-align:center"' if marker.startswith(":") else ' style="text-align:right"'
    return ' style="text-align:left"' if marker.startswith(":") else ""


def load_figure(path: Path) -> str:
    """Return a figure's SVG markup for inlining, refusing active content."""
    markup = path.read_text(encoding="utf-8")
    if not SVG_ROOT.search(markup):
        raise PaperError(f"figure is not an SVG document: {path.name}")
    if UNSAFE_SVG.search(markup):
        raise PaperError(f"figure holds a script, link or embedded resource: {path.name}")
    return markup[SVG_ROOT.search(markup).start():].strip()


def render_body(markdown: str, *, source: str, slugs: dict[str, str], pdf_route: str,
                figures: list[dict]) -> tuple[str, str]:
    """Return (title, body HTML) for a paper written in the library's Markdown subset."""
    lines = markdown.split("\n")
    out: list[str] = []
    paragraph: list[str] = []
    code: list[str] | None = None
    open_list: str | None = None
    title = ""
    pending = list(figures)
    paragraphs_written = 0

    def close_list() -> None:
        nonlocal open_list
        if open_list:
            out.append(f"</{open_list}>")
            open_list = None

    def flush() -> None:
        nonlocal paragraph, paragraphs_written
        # A line wrapped under a list item is not part of the list: the library
        # reader prints it after the list, and a <p> may not sit inside a <ul>.
        close_list()
        if paragraph:
            block, paragraph = paragraph, []
            joined = " ".join(block)
            own_pdf = re.fullmatch(r"\[[^\]]+\]\(([^)]+)\)", joined.strip())
            if own_pdf and own_pdf.group(1).endswith(pdf_route):
                pass  # a PDF does not need a link to itself
            elif all(METADATA_LINE.match(line) for line in block):
                out.append('<p class="meta">' + "<br>".join(inline(line, source, slugs) for line in block) + "</p>")
            else:
                paragraphs_written += 1
                lead = ' class="lead"' if paragraphs_written == 1 else ""
                out.append(f"<p{lead}>{inline(joined, source, slugs)}</p>")
                for figure in [item for item in pending if item["after_text"] in joined]:
                    pending.remove(figure)
                    out.append(f"<figure>{figure['markup']}<figcaption>"
                               f"{inline(figure['caption'], source, slugs)}</figcaption></figure>")

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            flush()
            if code is None:
                code = []
            else:
                out.append("<pre>" + escape("\n".join(code), quote=False) + "</pre>")
                code = None
        elif code is not None:
            code.append(line)
        elif not line.strip():
            flush()
        elif heading := re.match(r"^(#{1,6})\s+(.+)$", line):
            flush()
            level = len(heading.group(1))
            if level == 1 and not title:
                title = re.sub(r"[`*]", "", heading.group(2)).strip()
            out.append(f"<h{min(level, 6)}>{inline(heading.group(2), source, slugs)}</h{min(level, 6)}>")
        elif item := re.match(r"^\s*(?:[-*+]\s+|\d+\.\s+)(.+)$", line):
            if paragraph:
                flush()
            if not open_list:
                open_list = "ol" if re.match(r"^\s*\d", line) else "ul"
                out.append(f"<{open_list}>")
            out.append(f"<li>{inline(item.group(1), source, slugs)}</li>")
        elif re.match(r"^\s*---\s*$", line):
            flush()
            out.append("<hr>")
        else:
            headings = table_cells(line)
            markers = table_cells(lines[index + 1]) if index + 1 < len(lines) else []
            if headings and len(headings) == len(markers) and all(re.fullmatch(r":?-+:?", m) for m in markers):
                flush()
                aligns = [alignment(marker) for marker in markers]
                head = "".join(f'<th scope="col"{a}>{inline(h, source, slugs)}</th>'
                               for h, a in zip(headings, aligns, strict=True))
                rows = []
                index += 1
                while index + 1 < len(lines) and len(cells := table_cells(lines[index + 1])) == len(headings):
                    rows.append("<tr>" + "".join(
                        f"<td{a}>{inline(c, source, slugs)}</td>" for c, a in zip(cells, aligns, strict=True)
                    ) + "</tr>")
                    index += 1
                # A short table is easier to read whole than split across two pages.
                short = ' class="short"' if len(rows) <= SHORT_TABLE_ROWS else ""
                out.append(f"<table{short}><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>")
            else:
                paragraph.append(line)
        index += 1
    flush()
    if code is not None:
        out.append("<pre>" + escape("\n".join(code), quote=False) + "</pre>")
    if not title:
        raise PaperError("the paper has no '# ' title line")
    if pending:
        raise PaperError("no paragraph contains the figure anchor text: "
                         + "; ".join(repr(item["after_text"]) for item in pending))
    return title, "\n".join(out)


def render_html(markdown: str, *, source: str, slugs: dict[str, str], pdf_route: str, footer: str,
                figures: list[dict]) -> str:
    if '"' in footer or "\\" in footer or "\n" in footer:
        raise PaperError("the footer cannot hold a quote, a backslash or a line break")
    title, body = render_body(markdown, source=source, slugs=slugs, pdf_route=pdf_route, figures=figures)
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<title>{escape(title, quote=False)} · Oraclebot Research</title>\n"
            f"<style>{STYLE % {'footer': footer}}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n")


def inside_repository(relative: str, label: str) -> Path:
    """Resolve a build-file path and refuse one that leaves the repository."""
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise PaperError(f"{label} is outside the repository: {relative}")
    return path


def load_build(build_path: Path) -> dict:
    """Read a paper's build file and everything it names."""
    build = json.loads(build_path.read_text(encoding="utf-8"))
    if not isinstance(build, dict):
        raise PaperError("the build file must hold a JSON object")
    missing = [key for key in ("source", "output", "footer") if not isinstance(build.get(key), str)]
    if missing:
        raise PaperError(f"build file lacks {', '.join(missing)}")
    output = inside_repository(build["output"], "output")
    public = ROOT / "website/public"
    if not output.is_relative_to(public) or output.suffix != ".pdf":
        raise PaperError("output must be a .pdf under website/public")
    entries = build.get("figures", [])
    if not isinstance(entries, list):
        raise PaperError("figures must be a list")
    figures = []
    for number, item in enumerate(entries, start=1):
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str) for key in FIGURE_KEYS):
            raise PaperError(f"figure {number} needs {', '.join(FIGURE_KEYS)}, each as text")
        # Resolved from the build file's own folder, so a build file kept outside
        # the repository reaches the same "outside the repository" refusal.
        figure = inside_repository(str(build_path.resolve().parent / item["svg"]), "figure")
        figures.append({"after_text": item["after_text"], "caption": item["caption"], "markup": load_figure(figure)})
    return {
        "source": build["source"],
        "markdown": inside_repository(build["source"], "source").read_text(encoding="utf-8"),
        "output": output,
        "pdf_route": "/" + output.relative_to(public).as_posix(),
        "footer": build["footer"],
        "figures": figures,
    }


def find_chrome() -> str:
    chosen = os.environ.get("CHROME")
    if chosen:
        # A browser the author named must be the one that prints; falling back to
        # another would quietly change the PDF's fonts and layout.
        found = shutil.which(chosen)
        if not found:
            raise PaperError(f"CHROME does not name an executable browser: {chosen}")
        return found
    for candidate in CHROME_CANDIDATES:
        if found := shutil.which(candidate):
            return found
    raise PaperError("no Chrome or Chromium found; set CHROME to the browser binary")


def print_pdf(html: str, output: Path) -> None:
    """Print ``html`` to ``output`` with headless Chrome, replacing it only on success."""
    chrome = find_chrome()
    with tempfile.TemporaryDirectory(prefix="oraclebot-paper-") as work:
        page, pdf = Path(work) / "paper.html", Path(work) / "paper.pdf"
        page.write_text(html, encoding="utf-8")
        command = [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                   f"--user-data-dir={Path(work) / 'profile'}", f"--print-to-pdf={pdf}", page.as_uri()]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=CHROME_TIMEOUT_SECONDS,
                                    check=False)
        except subprocess.TimeoutExpired as error:
            raise PaperError(f"Chrome did not finish within {CHROME_TIMEOUT_SECONDS} seconds") from error
        if result.returncode != 0 or not pdf.is_file() or pdf.stat().st_size == 0:
            raise PaperError(f"Chrome did not write a PDF (exit {result.returncode}): {result.stderr.strip()[-400:]}")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdf, output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("build", type=Path, help="the paper's build file (JSON)")
    parser.add_argument("--html", type=Path, help="also write the print HTML here")
    parser.add_argument("--no-pdf", action="store_true", help="stop after the HTML")
    args = parser.parse_args(argv)
    try:
        build = load_build(args.build.resolve())
        html = render_html(build["markdown"], source=build["source"], slugs=catalog_slugs(),
                           pdf_route=build["pdf_route"], footer=build["footer"], figures=build["figures"])
        if args.html:
            args.html.write_text(html, encoding="utf-8")
        if not args.no_pdf:
            print_pdf(html, build["output"])
            print(f"Wrote {build['output'].relative_to(ROOT)} ({build['output'].stat().st_size:,} bytes)")
    except (PaperError, OSError, json.JSONDecodeError, KeyError) as error:
        print(f"build_paper: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build Oraclebot's public discovery documents from the published pages."""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "public"
ORIGIN = "https://oraclebot.io"
# One row per published working paper, newest first: its route, its slug in the
# research catalogue, its link title and a one-line summary. A PDF built with
# website/scripts/build_paper.py is published by adding its row here and its
# paragraph to research/index.md and research/index.html.
PAPERS = (
    ("/papers/hype-strategies-patterns-levels.pdf", "hype-strategies-patterns-levels-806597d4",
     "What holds up on HYPE? Strategies, patterns and price levels (PDF)",
     "Working paper on two years of HYPE backtests, price patterns and support and resistance levels."),
    ("/papers/zec-two-bar-reversal.pdf", "zec-two-bar-reversal-8b2f7af3",
     "Do two candles predict a ZEC reversal? (PDF)",
     "Exploratory working paper based on one day of observations."),
)
PAGES = (
    ("/", "index.md", "Public workspace overview and paper-trading limits."),
    ("/research/", "research/index.md", "Research journal, working papers and study limitations."),
)


def published_paper(slug: str) -> str:
    catalog = json.loads((PUBLIC / "research/catalog.json").read_bytes())
    paper = next((article for article in catalog["articles"] if article["slug"] == slug), None)
    if paper is None:
        raise ValueError(f"Working paper {slug} is not in the research catalogue; run export_research first")
    shard = json.loads((PUBLIC / paper["bodyPath"].lstrip("/")).read_bytes())
    return shard["articles"][paper["bodyKey"]]["body"]


def full_section(route: str, markdown: str) -> str:
    title, body = markdown.strip().split("\n", 1)
    if not title.startswith("# "):
        raise ValueError(f"Missing Markdown title for {route}")
    return f"{title}\nSource: {ORIGIN}{route}\n\n{body.lstrip()}\n"


def render() -> dict[str, bytes]:
    expected_pages = {route.strip("/") + "/index.html" if route != "/" else "index.html"
                      for route, _, _ in PAGES}
    built_pages = {file.relative_to(PUBLIC).as_posix() for file in PUBLIC.rglob("index.html")}
    # A PDF dropped into papers/ without a row above would be served but never
    # listed, so the set on disk must equal the set declared.
    listed_papers = {route.lstrip("/") for route, _, _, _ in PAPERS}
    built_papers = {file.relative_to(PUBLIC).as_posix() for file in (PUBLIC / "papers").glob("*.pdf")}
    if built_pages != expected_pages or built_papers != listed_papers:
        raise ValueError("Review discovery scope after changing a published page or paper")

    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    sitemap = ET.Element("urlset", {"xmlns": namespace})
    for route in [*(entry[0] for entry in PAGES), *(paper[0] for paper in PAPERS)]:
        ET.SubElement(ET.SubElement(sitemap, "url"), "loc").text = ORIGIN + route
    ET.indent(sitemap)

    index = [
        "# Oraclebot",
        "",
        "> Oraclebot is a research and paper-trading workspace for market signals, strategies, and historical backtests.",
        "",
        "## Public resources",
        "",
    ]
    full = ["<!-- Generated from the public Markdown pages and published working papers by website/scripts/build_discovery.py. -->"]
    for route, file, summary in PAGES:
        markdown = (PUBLIC / file).read_text(encoding="utf-8")
        title = markdown.splitlines()[0][2:]
        index.append(f"- [{title}]({ORIGIN}/{file}): {summary}")
        full.append(full_section(route, markdown))
    index.extend(f"- [{title}]({ORIGIN}{route}): {summary}" for route, _, title, summary in PAPERS)
    index.extend([
        "",
        "## Complete text",
        "",
        f"- [Full public text]({ORIGIN}/llms-full.txt): Readable Markdown for the public pages and working papers.",
        "",
    ])
    full.extend(full_section(route, published_paper(slug)) for route, slug, _, _ in PAPERS)

    return {
        "robots.txt": f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n".encode(),
        "sitemap.xml": ET.tostring(sitemap, encoding="utf-8", xml_declaration=True) + b"\n",
        "llms.txt": "\n".join(index).encode(),
        "llms-full.txt": "\n\n".join(full).encode(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, content in render().items():
        file = PUBLIC / name
        if args.check:
            if not file.is_file() or file.read_bytes() != content:
                raise SystemExit(f"Stale discovery asset: {file.name}. Run python3 -m website.scripts.build_discovery.")
        else:
            file.write_bytes(content)


if __name__ == "__main__":
    main()

"""Build Oraclebot's public discovery documents from the published pages."""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "public"
ORIGIN = "https://oraclebot.io"
PAPER_ROUTE = "/papers/zec-two-bar-reversal.pdf"
PAPER_SLUG = "zec-two-bar-reversal-8b2f7af3"
PAGES = (
    ("/", "index.md", "Public workspace overview and paper-trading limits."),
    ("/research/", "research/index.md", "Research journal, working paper and study limitations."),
)


def published_paper() -> str:
    catalog = json.loads((PUBLIC / "research/catalog.json").read_bytes())
    paper = next(article for article in catalog["articles"] if article["slug"] == PAPER_SLUG)
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
    if built_pages != expected_pages or not (PUBLIC / PAPER_ROUTE.lstrip("/")).is_file():
        raise ValueError("Review discovery scope after changing a published page or paper")

    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    sitemap = ET.Element("urlset", {"xmlns": namespace})
    for route in [*(entry[0] for entry in PAGES), PAPER_ROUTE]:
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
    full = ["<!-- Generated from the public Markdown pages and published working paper by website/scripts/build_discovery.py. -->"]
    for route, file, summary in PAGES:
        markdown = (PUBLIC / file).read_text(encoding="utf-8")
        title = markdown.splitlines()[0][2:]
        index.append(f"- [{title}]({ORIGIN}/{file}): {summary}")
        full.append(full_section(route, markdown))
    index.extend([
        f"- [Do two candles predict a ZEC reversal? (PDF)]({ORIGIN}{PAPER_ROUTE}): Exploratory working paper based on one day of observations.",
        "",
        "## Complete text",
        "",
        f"- [Full public text]({ORIGIN}/llms-full.txt): Readable Markdown for the public pages and working paper.",
        "",
    ])
    full.append(full_section(PAPER_ROUTE, published_paper()))

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

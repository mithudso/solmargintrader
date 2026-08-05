"""Generate `docs/CONCEPTS.md` — the conceptual index, as prose.

    python3 index/make_concepts_doc.py
    python3 index/make_concepts_doc.py --stdout

Reads `index/CONCEPT-INDEX.json`, so run `python3 index/build.py all` first.

The concepts are not an invented taxonomy. Each one comes from vocabulary the repo
already uses — the `FAMILY` dict in `backtester/core/strategies/__init__.py`, the
strategy-card frontmatter keys, `docs/trading-signals-concept-family.md`, and terms
verified to recur across the corpus. A concept that matches no file is dropped by
the builder rather than kept for symmetry, and the count of dropped ones is
reported so the omission is visible.

What this answers that a text search cannot: *"which files bear on this idea"*,
where the idea has many names. "Evidence floor" appears as `min_total_turnover`,
`insufficient`, `DROPPED` and `rankable` depending on the file, and no single
keyword finds all four.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "index" / "CONCEPT-INDEX.json"
DEST = REPO / "docs" / "CONCEPTS.md"


def render(con: dict) -> str:
    curated = [c for c in con["concepts"] if not c["id"].startswith("family:")]
    families = [c for c in con["concepts"] if c["id"].startswith("family:")]

    out: list[str] = [
        "# Conceptual index",
        "",
        f"**Generated** from `index/CONCEPT-INDEX.json` ({con['generatedAt']}). "
        f"{con['counts']['concepts']} concepts.",
        "",
        "```bash",
        "python3 index/build.py all              # refresh",
        "python3 index/make_concepts_doc.py      # rewrite this file",
        "python3 index/search.py --concepts      # list them",
        "python3 index/search.py --concept cpcv  # files for one",
        "```",
        "",
        "## What this is for",
        "",
        "A text search finds a word; this finds an *idea* under all the names it goes "
        "by in this repo. The evidence floor, for instance, appears as "
        "`min_total_trades`, `insufficient`, `DROPPED` and `rankable` in different "
        "files, and no single keyword finds all four.",
        "",
        "**The concepts are the repo's own vocabulary, not a taxonomy imposed on it.** "
        "They are drawn from the `FAMILY` dict in "
        "`backtester/core/strategies/__init__.py`, the strategy-card frontmatter, "
        "`docs/trading-signals-concept-family.md`, and terms verified to recur in the "
        "corpus. A concept matching no file is dropped rather than kept — "
        + (f"{con['counts']['dropped']} were dropped on the last build "
           f"({', '.join(con['droppedForNoMatches'])})."
           if con["counts"]["dropped"] else
           "none were dropped on the last build, so every concept below is real.")
        + "",
        "",
        "## Method concepts",
        "",
        "The ideas that decide whether a number in this repo means anything. Ordered by "
        "how many files touch them.",
        "",
    ]
    for c in curated:
        out += [
            f"### {c['label']}",
            "",
            f"`{c['id']}` · **{c['matchingFiles']} files** · "
            f"matched on {', '.join(f'`{t}`' for t in c['terms'])}",
            "",
            f"{c['why']}",
            "",
            "Strongest files:",
            "",
        ]
        for f in c["files"][:8]:
            out.append(f"- `{f['path']}` ({f['hits']} hits)")
        out += ["",
                f"Full list: `python3 index/search.py --concept {c['id']} -n "
                f"{c['matchingFiles']}`", ""]

    out += [
        "---",
        "",
        "## Strategy families",
        "",
        "These are not editorial: each is a value of the `FAMILY` dict in "
        "`backtester/core/strategies/__init__.py`, which is what the engine itself uses "
        "to decide that two signals measure the same thing (the combination sweep skips "
        "same-family pairs for exactly that reason).",
        "",
        "The families also carry a measured finding. Of the 25 registered strategies run "
        "on five assets, the eight positive on all five are drawn from breakout, trend, "
        "momentum, regime-filter and volume-flow — and **not one is from a reversion "
        "family**. No reversion-family strategy clears all five. See "
        "`research/CROSS-ASSET-TRANSFER.md`.",
        "",
        "| Family | Files | Matched on |",
        "|---|---|---|",
    ]
    for c in families:
        fam = c["id"].split(":", 1)[1]
        out.append(f"| `{fam}` | {c['matchingFiles']} | "
                   + ", ".join(f"`{t}`" for t in c["terms"]) + " |")
    out.append("")

    axes = con.get("cardAxes") or {}
    if axes:
        out += [
            "---",
            "",
            "## Strategy-card axes",
            "",
            "Facts already written in the 46 cards' frontmatter, inverted so a value "
            "points back at its cards. Useful for questions the prose does not index — "
            "\"which specs were never implemented\", \"which are rated very-low and why\".",
            "",
        ]
        for axis, values in axes.items():
            out += [f"### `{axis}`", ""]
            for val, paths in sorted(values.items(), key=lambda x: -len(x[1])):
                names = ", ".join(f"`{Path(p).stem}`" for p in paths[:12])
                more = f" and {len(paths) - 12} more" if len(paths) > 12 else ""
                out.append(f"- **{val}** ({len(paths)}) — {names}{more}")
            out.append("")

    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args(argv)
    if not SRC.exists():
        sys.exit("index/CONCEPT-INDEX.json is missing. Run: python3 index/build.py all")
    con = json.loads(SRC.read_text())
    text = render(con)
    if args.stdout:
        print(text)
        return 0
    DEST.parent.mkdir(exist_ok=True)
    DEST.write_text(text)
    print(f"{DEST.relative_to(REPO)}: {con['counts']['concepts']} concepts, "
          f"{len(text.splitlines()):,} lines")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

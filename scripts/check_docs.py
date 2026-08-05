#!/usr/bin/env python3
"""Fail the build when the docs drift from the repo.

    python3 scripts/check_docs.py
    python3 scripts/check_docs.py --prune     # drop dead index entries

Two kinds of rot, both of which happened here before this existed:

  * **Stale test counts.** The docs claimed 250 backtester tests for several
    commits while the suite had grown to 454. A count in prose is a claim about
    the code, so it is checked against the code.
  * **Dead index entries.** `docs/high_signal_file_index.json` and
    `docs/codebase-overview.md` name files for LLM retrieval. A renamed module
    leaves an entry pointing at nothing, and the failure mode is silent: the
    reader is told a file exists and believes it.

Counts come from unittest *discovery*, not from running the suites -- soltui's
tests take ~70s and this has to be cheap enough to run on every commit. The
extension count is read from its own test files for the same reason.

Exit codes: 0 clean, 1 drift found.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Suite name -> (test directory, the label the docs use for it).
SUITES: dict[str, tuple[str, str]] = {
    "backtester": ("backtester/tests", "backtester"),
    "soltui": ("soltui/tests", "soltui"),
}

# Docs that quote a test count, and the suite each quoted number belongs to.
# The pattern is the count immediately followed by "tests" on the same line as
# the suite's discover command, or in a heading naming the suite.
COUNT_DOCS = ("README.md", "CLAUDE.md", "docs/TESTING.md", "docs/ARCHITECTURE.md")

INDEX_JSON = "docs/high_signal_file_index.json"
OVERVIEW_MD = "docs/codebase-overview.md"


def is_ignored(rel: str) -> bool:
    """True when git deliberately ignores `rel`.

    `data/` and `results/` are regenerable and gitignored, so a fresh clone has
    neither. Without this, the docs could only pass the check on a machine that
    had already run a fetch -- which is exactly backwards, since CI is the one
    place guaranteed not to have them.

    Both spellings are tried because `.gitignore` writes directory rules with a
    trailing slash, and `check-ignore` will not match that rule against a bare
    name when the directory is absent -- the case this has to answer.
    """
    for candidate in (rel, f"{rel}/"):
        done = subprocess.run(
            ["git", "check-ignore", "-q", "--", candidate],
            cwd=REPO,
            capture_output=True,
        )
        if done.returncode == 0:
            return True
    return False


def missing_and_tracked(rel: str) -> bool:
    """True when a documented path is absent for a reason worth failing over."""
    return not (REPO / rel).exists() and not is_ignored(rel)


def count_suite(rel_dir: str) -> int:
    """Number of test cases discovery finds under `rel_dir`, without running them."""
    suite = unittest.defaultTestLoader.discover(
        str(REPO / rel_dir), top_level_dir=str(REPO)
    )

    def walk(s: unittest.TestSuite | unittest.TestCase) -> int:
        if isinstance(s, unittest.TestSuite):
            return sum(walk(child) for child in s)
        # A load error is itself a _FailedTest case; count it so a broken import
        # shows up as a count mismatch rather than a silently smaller suite.
        return 1

    return walk(suite)


def count_extension_tests() -> int:
    """`node:test` cases in `extension/test`, counted by source.

    Counts `test(`/`it(` at the start of a line, which is how every file in that
    directory declares a case. Reading the source rather than running `node
    --test` keeps this check under a second.
    """
    total = 0
    pattern = re.compile(r"^\s*(?:test|it)\s*\(", re.MULTILINE)
    for path in sorted((REPO / "extension" / "test").glob("*.test.js")):
        total += len(pattern.findall(path.read_text(encoding="utf-8")))
    return total


def claimed_counts(text: str) -> dict[str, list[int]]:
    """Every `N tests` claim in `text`, bucketed by the suite it names.

    A claim is attributed by what else is on the line: a `discover -s <dir>`
    command, an `npm test`, or a heading naming the suite.
    """
    found: dict[str, list[int]] = {"backtester": [], "soltui": [], "extension": []}
    for line in text.splitlines():
        match = re.search(r"(\d[\d,]*)\s+tests\b", line)
        if not match:
            continue
        value = int(match.group(1).replace(",", ""))
        lowered = line.lower()
        if "soltui" in lowered:
            found["soltui"].append(value)
        elif "backtester" in lowered or "research" in lowered:
            found["backtester"].append(value)
        elif "npm test" in lowered or "extension" in lowered:
            found["extension"].append(value)
        # A count naming no suite is ignored rather than guessed at.
    return found


def check_counts(actual: dict[str, int]) -> list[str]:
    """Compare every claimed count in the docs against the real one."""
    problems: list[str] = []
    for rel in COUNT_DOCS:
        path = REPO / rel
        if not path.exists():
            problems.append(f"{rel}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        for suite, values in claimed_counts(text).items():
            for value in values:
                if value != actual[suite]:
                    problems.append(
                        f"{rel}: claims {value} {suite} tests, actual {actual[suite]}"
                    )
    return problems


def check_index(prune: bool) -> list[str]:
    """Every path named by the retrieval index must exist."""
    path = REPO / INDEX_JSON
    if not path.exists():
        return [f"{INDEX_JSON}: missing"]
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("files", [])
    dead = [e for e in entries if missing_and_tracked(e["path"])]
    if not dead:
        return []
    if prune:
        data["files"] = [e for e in entries if not missing_and_tracked(e["path"])]
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return [f"{INDEX_JSON}: pruned {len(dead)} dead entr(y/ies)"]
    return [f"{INDEX_JSON}: dead entry {e['path']}" for e in dead]


def check_overview() -> list[str]:
    """Every backtick-quoted repo path in the overview must exist.

    Only paths that look like real files (contain a `/` and a `.`) are checked,
    so prose like `on_bar` or `REGISTRY` is left alone.
    """
    path = REPO / OVERVIEW_MD
    if not path.exists():
        return [f"{OVERVIEW_MD}: missing"]
    text = path.read_text(encoding="utf-8")
    problems = []
    for candidate in sorted(set(re.findall(r"`([\w./-]+/[\w.-]+\.\w+)`", text))):
        if missing_and_tracked(candidate):
            problems.append(f"{OVERVIEW_MD}: names missing file {candidate}")
    return problems


def check_components_covered() -> list[str]:
    """The overview must have a section per workspace component.

    A missing component section is the failure this repo actually had: soltui
    existed for weeks with 95 tests and appeared in no top-level document.
    """
    path = REPO / OVERVIEW_MD
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").lower()
    return [
        f"{OVERVIEW_MD}: no section for component {name}/"
        for name in ("backtester", "research", "extension", "soltui")
        if f"{name}/" not in text
    ]


def main(argv: list[str] | None = None) -> int:
    """Run every check and report all problems at once."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--prune", action="store_true", help="remove dead entries from the JSON index"
    )
    args = ap.parse_args(argv)

    actual = {name: count_suite(d) for name, (d, _) in SUITES.items()}
    actual["extension"] = count_extension_tests()

    problems = (
        check_counts(actual)
        + check_index(args.prune)
        + check_overview()
        + check_components_covered()
    )

    for line in problems:
        print(f"drift: {line}", file=sys.stderr)
    counts = ", ".join(f"{k} {v}" for k, v in sorted(actual.items()))
    print(f"suite counts: {counts}")
    if problems:
        print(f"{len(problems)} problem(s); see above", file=sys.stderr)
        return 1
    print("docs agree with the repo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate `docs/FILES.md` — every tracked file, its purpose, contents and use.

    python3 index/make_files_doc.py            # writes docs/FILES.md
    python3 index/make_files_doc.py --stdout   # preview without writing

Reads `index/INDEX.json`, so run `python3 index/build.py all` first.

**Why a generator and not a hand-written document.** 237 files hand-maintained
would be stale within a week, and this repo has already been bitten twice by
artifacts nobody re-derived. So the descriptions are assembled from three sources,
and every entry says which one it came from:

- **curated** — the `CURATED` table below. Hand-written `purpose` and `use` for
  the files where extraction cannot supply what a reader needs: the engine, the
  research drivers, the extension's risk path, and the seventeen files with no
  prose of their own (empty `__init__.py`, dotfiles, HTML/CSS, a binary icon).
- **extracted** — the file's own module docstring, JSDoc header, or frontmatter
  `summary`. 63 of 67 Python modules and all 27 JS files carry a substantial one,
  which is why extraction is worth trusting here.
- **derived** — shape only, for generated artifacts: a CSV's header and row count,
  a JSON's keys. Prose for a result file would be invented.

The curation lives in this module as data rather than in the Markdown, so
regenerating never discards it. Add a file to `CURATED` and it stays curated.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
INDEX_JSON = REPO / "index" / "INDEX.json"
DEST = REPO / "docs" / "FILES.md"

# Ordering of the top-level sections: what a newcomer should read in sequence.
DIR_ORDER = ["(root)", "docs", "index", "backtester", "research", "extension",
             "soltui", ".github", "tradingskilllist", ".remember"]

DIR_INTROS: dict[str, str] = {
    "(root)": "Repository-level entry points and agent instructions. `AGENTS.md` and "
              "`CLAUDE.md` are the operative rules for anyone — human or agent — "
              "changing this repo; read them before the code.",
    "docs": "Curated prose. `ARCHITECTURE.md` explains how the pieces fit, "
            "`TESTING.md` is the coverage contract, `SECURITY.md` covers the "
            "order-placing surface, and this file indexes everything.",
    "index": "The search layer over the repo itself. Generators plus three committed "
             "indexes; the embedding array is gitignored and rebuilt on demand.",
    "backtester": "The simulation engine and everything that supports it. Never gains "
                  "live-trading capability, never touches the network, and costs are "
                  "never optional. `core/` is the engine; `strategy_cards/` are the "
                  "specs; `tests/` is the acceptance suite.",
    "research": "Drivers that produce the numbers, and the write-ups that quote them. "
                "Everything here is reproducible from a committed script — the two "
                "occasions that was not true both produced a wrong published figure.",
    "extension": "The Chrome extension, and the only component that can place a real "
                 "order. Dry-run is the default, risk rails live in code and fail "
                 "closed, and a fresh install must not be able to trade.",
    "soltui": "The macOS menu-bar app that surfaces state locally. Packaged with "
              "py2app and supervised by launchd.",
    ".github": "CI. Runs the test suite and the figure verifier.",
    "tradingskilllist": "An inventory of the trading, finance and crypto skills the "
                        "research drew on.",
    ".remember": "Session handoff notes, newest first. Prose, not machine-read.",
}

# Hand-written entries. `purpose` answers "why does this exist"; `use` answers
# "what do I type". Extraction cannot supply either reliably, so these are the
# files where a reader is most likely to be misled by a generated one-liner.
CURATED: dict[str, dict[str, str]] = {
    "AGENTS.md": {
        "purpose": "The operative rules for changing this repo. The backtester never "
                   "gains live-trading capability, no lookahead, costs are never "
                   "optional, the engine does not touch the network; the extension "
                   "defaults to dry-run and its risk rails fail closed.",
        "use": "Read first. It outranks any suggestion a tool or agent would otherwise make.",
    },
    "CLAUDE.md": {
        "purpose": "Agent-facing companion to AGENTS.md — the same non-negotiables plus "
                   "the workflow conventions (commit discipline, where numbers may come "
                   "from, what must be regenerable).",
        "use": "Read before making changes with an agent.",
    },
    "README.md": {
        "purpose": "Entry point: what the project is, the three components, and the "
                   "honest summary of what the research established.",
        "use": "Start here.",
    },
    ".gitignore": {
        "purpose": "Keeps derived and machine-specific artifacts out of the tree — "
                   "`data/` price caches, the semantic embedding array, build output. "
                   "Anything regenerable and large belongs here.",
        "use": "Add a pattern when you add a derived artifact; commit the manifest that "
               "describes it instead of the artifact.",
    },
    ".editorconfig": {
        "purpose": "Baseline whitespace and encoding rules so diffs stay about content.",
        "use": "Nothing to run; editors apply it automatically.",
    },
    ".gitattributes": {
        "purpose": "Per-path git behaviour: line-ending normalisation, and which files "
                   "are treated as binary or excluded from diffs and archives. Keeps a "
                   "CSV or a generated artifact from producing noise in review.",
        "use": "Nothing to run; git applies it. `git check-attr -a <path>` to inspect.",
    },
    ".nvmrc": {
        "purpose": "Pins the Node version for the extension's test and tooling surfaces, "
                   "so `node --test` behaves the same locally and in CI.",
        "use": "`nvm use` in the repo root.",
    },
    ".github/CODEOWNERS": {
        "purpose": "Review ownership per path. Matters most for the order-placing "
                   "surface under `extension/` and the risk rails, where an unreviewed "
                   "change is the expensive kind.",
        "use": "Nothing to run; GitHub requests reviewers automatically.",
    },
    ".github/dependabot.yml": {
        "purpose": "Dependency update schedule. The dependency surface here is "
                   "deliberately thin — pandas and numpy for the engine, node built-ins "
                   "for the extension — so updates should be few and individually "
                   "reviewable.",
        "use": "Nothing to run; GitHub opens PRs on the configured schedule.",
    },
    ".github/workflows/ci.yml": {
        "purpose": "The gate. Runs the Python suite and `research/verify_numbers.py`, so "
                   "a documented figure that no longer matches its result file fails the "
                   "build rather than surviving in prose.",
        "use": "Runs on push. Reproduce locally with `python3 -m pytest backtester/tests -q` "
               "and `python3 research/verify_numbers.py`.",
    },
    "backtester/core/__init__.py": {
        "purpose": "Marks `backtester.core` as a package. Intentionally empty — the "
                   "engine's public surface is the individual modules, so nothing is "
                   "re-exported here and there is no import-time side effect.",
        "use": "Import the module you need directly, e.g. `from backtester.core.engine "
               "import run_backtest`.",
    },
    "backtester/tests/__init__.py": {
        "purpose": "Makes the test directory a package so `python3 -m unittest discover "
                   "-t .` resolves `backtester.*` imports. Empty by design.",
        "use": "Nothing to run.",
    },
    "soltui/__init__.py": {
        "purpose": "Package marker for the menu-bar app. Empty.",
        "use": "Nothing to run.",
    },
    "soltui/tests/__init__.py": {
        "purpose": "Package marker for the app's tests. Empty.",
        "use": "Nothing to run.",
    },
    "soltui/soltui-service": {
        "purpose": "Install-and-supervise script for the menu-bar app: builds the py2app "
                   "bundle, writes the launchd agent, and manages the flag file that is "
                   "the real off switch (because `KeepAlive` necessarily overrides the "
                   "app's own Quit item).",
        "use": "`python3 soltui/soltui-service status|start|stop|build`.",
    },
    "soltui/SolTUI.icns": {
        "purpose": "macOS app icon for the packaged bundle.",
        "use": "Referenced by the py2app build; nothing to run.",
    },
    "soltui/requirements.txt": {
        "purpose": "Runtime dependencies for the menu-bar app (rumps/pyobjc and the "
                   "py2app build tooling).",
        "use": "`python3 -m pip install -r soltui/requirements.txt`.",
    },
    "backtester/requirements.txt": {
        "purpose": "Dependencies for the engine and research drivers — deliberately thin: "
                   "pandas and numpy. No network client, no broker SDK, nothing that "
                   "could place an order.",
        "use": "`python3 -m pip install -r backtester/requirements.txt`.",
    },
    "extension/manifest.json": {
        "purpose": "MV3 manifest: permissions, the service worker entry point, and the "
                   "UI surfaces. The permission list is the extension's blast radius, so "
                   "review any addition against `docs/SECURITY.md`.",
        "use": "Load unpacked from `extension/` in `chrome://extensions`.",
    },
    "extension/package.json": {
        "purpose": "Node scripts for the extension's test and tooling surfaces.",
        "use": "`npm test` inside `extension/`.",
    },
    "extension/src/ui/popup.html": {
        "purpose": "Browser-action popup shell — status at a glance and the dry-run "
                   "toggle. Markup only; behaviour lives in the JS modules.",
        "use": "Opens from the toolbar icon.",
    },
    "extension/src/ui/dashboard.html": {
        "purpose": "Full-page dashboard shell for open state, ladder rungs and recent "
                   "ticks. Markup only.",
        "use": "Opened from the popup.",
    },
    "extension/src/ui/ui.css": {
        "purpose": "Shared styling for both surfaces, kept in one file so the popup and "
                   "dashboard cannot drift visually.",
        "use": "Linked by the HTML; nothing to run.",
    },
    "extension/test/core.test.js": {
        "purpose": "Node test-runner suite for the pure core — grid maths, planner, "
                   "reconciler. No `chrome.*`, so it runs headless.",
        "use": "`node --test extension/test/` or `npm test` in `extension/`.",
    },
    "extension/test/surfaces.test.js": {
        "purpose": "Covers the command registry as driven by each surface (popup, "
                   "dashboard, CLI), so one registry change cannot silently break one "
                   "caller.",
        "use": "`node --test extension/test/`.",
    },
    "extension/test/wallet.test.js": {
        "purpose": "Wallet and signing path tests, including the refusals — the cases "
                   "that must NOT produce a transaction.",
        "use": "`node --test extension/test/`.",
    },
    "pagesource": {
        "purpose": "A captured page source kept as a fixture for the scraping/parsing "
                   "work. Reference data, not code.",
        "use": "Read it; nothing to run.",
    },
    "research/results/cpcv_tables.md": {
        "purpose": "Generated Markdown tables from the CPCV sweep — the human-readable "
                   "face of `cpcv_results.csv`, including the IQR column the headline "
                   "medians must be read against.",
        "use": "Regenerate with `python3 research/cpcv_sweep.py`. Read alongside "
               "`research/RANKED_LISTS.md`.",
    },
    "backtester/core/engine.py": {
        "purpose": "The event loop: maps a strategy's target exposure to fills, applies "
                   "costs exactly once, and marks the book every bar. `fill_delay=1` is "
                   "what keeps a signal at bar t from being filled at bar t.",
        "use": "`from backtester.core.engine import run_backtest, EngineConfig`. Every "
               "reported figure in this repo comes through here.",
    },
    "backtester/core/cpcv.py": {
        "purpose": "Combinatorial purged cross-validation and PBO. Produces a "
                   "distribution of out-of-sample paths instead of one split, and "
                   "measures whether the in-sample ranking predicts anything.",
        "use": "`from backtester.core.cpcv import cpcv_evaluate, pbo_cscv`. Note that a "
               "configuration below `min_total_trades` is marked `insufficient` and "
               "printed DROPPED but still returns a full path count.",
    },
    "backtester/core/data.py": {
        "purpose": "Loading and validating bars. Refuses gaps rather than filling them, "
                   "resolves columns by name, and requires monotone de-duplicated "
                   "timestamps — a forward-filled gap flatters every volatility and "
                   "reversion statistic computed after it.",
        "use": "`CsvLoader(path, allow_gaps=False).load(asset, start, end, interval)`.",
    },
    "backtester/core/strategies/__init__.py": {
        "purpose": "The strategy registry and the `FAMILY` taxonomy. `build(name, **params)` "
                   "and `build_composite(specs, mode)` are the only sanctioned ways to "
                   "construct a configuration, so the registry stays the single source of "
                   "truth for what exists.",
        "use": "`from backtester.core.strategies import build, build_composite, FAMILY`.",
    },
    "research/sweep.py": {
        "purpose": "Defines `HORIZONS` — the per-horizon data file, interval, gap policy "
                   "and parameter set — and runs the single-split walk-forward that CPCV "
                   "superseded. The parameter tables here are what every other driver "
                   "imports, so an edit moves every downstream number.",
        "use": "`python3 research/sweep.py --help`. Imported by the other drivers for "
               "`HORIZONS` and `load_horizon`.",
    },
    "research/cpcv_sweep.py": {
        "purpose": "The primary evaluation driver: CPCV over singles, pairs and triples, "
                   "then PBO across the configuration set. Prints its own legend so the "
                   "numbers cannot travel without their meaning.",
        "use": "`python3 research/cpcv_sweep.py --horizon medium --groups 8 --k 2`.",
    },
    "research/cross_asset_cpcv.py": {
        "purpose": "Runs the registered strategy set on another coin with the SOL-tuned "
                   "parameters deliberately NOT refitted, so the measurement is transfer "
                   "rather than fit. Two gates: it reproduces the committed BTC/ETH "
                   "reference, and reproduces SOL's five published medians.",
        "use": "`python3 research/cross_asset_cpcv.py --self-test` then "
               "`--assets SOL,DOGE,ZEC` or `--top5 --assets DOGE,ZEC`.",
    },
    "research/perturb.py": {
        "purpose": "The second independent robustness axis: nudge each parameter ±10% and "
                   "re-run CPCV. A point that collapses under a small nudge was fitted to "
                   "noise, whatever its Sharpe.",
        "use": "`python3 research/perturb.py --help`.",
    },
    "research/verify_numbers.py": {
        "purpose": "The figure gate. Re-checks every number quoted in `RANKED_LISTS.md` "
                   "and `STRATEGIES.md` against the result files that produced them, so a "
                   "transcription slip cannot survive in prose. CI runs it.",
        "use": "`python3 research/verify_numbers.py` — currently 950 figures, exit 0.",
    },
    "research/turnover_table.py": {
        "purpose": "The one comparable turnover table for the ten coins, plus a checker. "
                   "Exists because ten spokes each pulling their own snapshot produced ten "
                   "figures that were ranked against each other anyway, and the ranking "
                   "was wrong.",
        "use": "`python3 research/turnover_table.py` or `--check`.",
    },
    "research/geometry.py": {
        "purpose": "Sensitivity of results to the CPCV geometry itself. Changing 8 blocks "
                   "to 9 moved the best pair's median Sharpe more than the worst parameter "
                   "nudge did — the evaluation design mattered more than the strategy.",
        "use": "`python3 research/geometry.py --help`.",
    },
    "index/build.py": {
        "purpose": "Builds the four indexes over every tracked file: metadata, BM25 text, "
                   "concepts, and the opt-in semantic embeddings. `--check` re-hashes the "
                   "tree so a stale index fails loudly.",
        "use": "`python3 index/build.py all`, then `semantic` for embeddings, and "
               "`--check` before trusting it.",
    },
    "index/search.py": {
        "purpose": "Query the index three ways — exact (BM25), meaning (cosine over "
                   "embeddings), or concept — with rank fusion as the default because a "
                   "reader rarely knows which kind of query they are typing.",
        "use": "`python3 index/search.py \"how are costs applied\"`, `--concepts`, "
               "`--concept <id>`, `--file <path>`, `--kind code-python`.",
    },
    "index/make_files_doc.py": {
        "purpose": "Generates `docs/FILES.md` from the index plus the curated table in "
                   "this module, so per-file documentation is regenerable and curation is "
                   "never discarded by a rebuild.",
        "use": "`python3 index/make_files_doc.py`.",
    },
}

# How to use a file, inferred from what it is, when no curated entry exists.
def derived_use(e: dict[str, Any]) -> str:
    path, kind, ext = e["path"], e["kind"], e["ext"]
    syms = e.get("symbols") or []
    if kind == "test":
        if ext == ".js":
            return "`node --test extension/test/`"
        return f"`python3 -m pytest {path} -q`"
    if kind == "strategy-card":
        fm = e.get("frontmatter") or {}
        key = fm.get("registry_key")
        if key and key not in {"null", "None"}:
            return (f"Read the card, then build it: "
                    f"`build('{key}', **params)`. Status: {fm.get('status', '?')}.")
        return (f"Specification only — read it; there is no runner. "
                f"Status: {fm.get('status', '?')}.")
    if kind == "result":
        if ext == ".csv":
            return f"`pandas.read_csv('{path}')` — regenerate with the driver that names it."
        if ext == ".json":
            return f"`json.load(open('{path}'))`"
        return "Read it; regenerate with the driver that produced it."
    if kind in {"doc", "coin-reference"}:
        return "Read it."
    if kind == "code-python":
        if "main()" in syms or "argparse" in (e.get("imports") or []):
            return f"`python3 {path} --help`"
        mod = path.replace("/", ".").removesuffix(".py")
        return f"`import {mod}`"
    if kind == "code-js":
        return "Loaded by the extension; see `extension/manifest.json` for entry points."
    if kind == "config":
        return "Configuration; nothing to run."
    return "Read it."


def contents_of(e: dict[str, Any]) -> str:
    bits: list[str] = []
    syms = e.get("symbols") or []
    if syms:
        shown = ", ".join(f"`{s}`" for s in syms[:10])
        bits.append(f"Defines {shown}" + (f" and {len(syms) - 10} more" if len(syms) > 10 else ""))
    # A derived CSV purpose already states the shape; repeating it here would say
    # the same thing twice, so only the full column list is added.
    if e.get("csvHeader"):
        cols = ", ".join(f"`{c}`" for c in e["csvHeader"])
        if e.get("summarySource") == "derived":
            bits.append(f"Columns: {cols}")
        else:
            bits.append(f"{e.get('csvRows', 0):,} rows × {len(e['csvHeader'])} columns: {cols}")
    fm = e.get("frontmatter") or {}
    keep = {k: fm[k] for k in ("status", "family", "evaluation", "success_likelihood",
                               "data_available", "registry_key") if fm.get(k)}
    if keep:
        bits.append("Frontmatter: " + ", ".join(f"`{k}`={v}" for k, v in keep.items()))
    internal = e.get("internalImports") or []
    if internal:
        bits.append("Depends on " + ", ".join(f"`{m}`" for m in internal))
    return ". ".join(bits) + "." if bits else ""


def render(meta: dict[str, Any]) -> str:
    by_dir: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in meta["files"]:
        top = (e["dir"].split("/")[0] if e["dir"] else "(root)") or "(root)"
        by_dir[top].append(e)

    c = meta["counts"]
    n_cur = sum(1 for e in meta["files"] if e["path"] in CURATED)
    out: list[str] = [
        "# Every file in this repository",
        "",
        f"**Generated** from `index/INDEX.json` at commit `{meta.get('commit')}` "
        f"({meta['generatedAt']}). {c['files']} tracked files, "
        f"{c['bytes'] / 1e6:.1f} MB.",
        "",
        "Regenerate with:",
        "",
        "```bash",
        "python3 index/build.py all          # refresh the index",
        "python3 index/make_files_doc.py     # rewrite this file",
        "python3 index/build.py --check      # fail if the index is stale",
        "```",
        "",
        "## How to read an entry",
        "",
        "Every entry marks where its description came from, because a generated "
        "one-liner and a considered one should not look alike:",
        "",
        f"- **curated** ({n_cur} files) — hand-written purpose and usage, in the "
        "`CURATED` table of `index/make_files_doc.py`. Used where extraction cannot "
        "give a reader what they need: the engine, the research drivers, the "
        "order-placing path, and the files with no prose of their own.",
        f"- **extracted** — the file's own module docstring, JSDoc header, or "
        "frontmatter `summary`. Trustworthy here because 63 of 67 Python modules and "
        "all 27 JS files carry a substantial one.",
        "- **derived** — shape only, for generated artifacts: a CSV's header and row "
        "count, a JSON's keys. Prose for a result file would be invented.",
        "",
        "*How to use* is curated where it matters and otherwise inferred from the file's "
        "kind — a test gets its runner, a CLI gets `--help`, a module gets its import path.",
        "",
        "## Related documents",
        "",
        "This file is the **exhaustive** one: every tracked file, no exceptions, "
        "regenerated from the index. For orientation rather than lookup, read these "
        "first — they are shorter and they explain *why* the pieces fit together:",
        "",
        "- `docs/codebase-overview.md` — the narrative tour.",
        "- `docs/ARCHITECTURE.md` — how the three components relate.",
        "- `docs/COMPONENTS.md` — component-level responsibilities.",
        "- `docs/CONCEPTS.md` — the conceptual index: which files bear on which idea.",
        "",
        "To *search* rather than browse: `python3 index/search.py \"your question\"`.",
        "",
        "## Contents",
        "",
    ]
    order = [d for d in DIR_ORDER if d in by_dir] + \
            sorted(d for d in by_dir if d not in DIR_ORDER)
    for d in order:
        out.append(f"- [`{d}`](#{d.strip('.()').lower().replace('/', '')}) — "
                   f"{len(by_dir[d])} files")
    out.append("")

    for d in order:
        entries = sorted(by_dir[d], key=lambda x: (x["dir"], x["name"]))
        out += ["---", "", f"## {d}", ""]
        if DIR_INTROS.get(d):
            out += [DIR_INTROS[d], ""]
        out.append(f"{len(entries)} files.")
        out.append("")
        current_sub = None
        for e in entries:
            if e["dir"] != current_sub:
                current_sub = e["dir"]
                if current_sub and current_sub != d:
                    out += [f"### `{current_sub}/`", ""]
            cur = CURATED.get(e["path"])
            purpose = cur["purpose"] if cur else (e["summary"] or "_No description available._")
            src = "curated" if cur else (
                "derived" if e["summarySource"] == "derived" else
                "extracted" if e["summarySource"] != "none" else "none")
            use = cur["use"] if cur else derived_use(e)
            contents = contents_of(e)

            out.append(f"#### `{e['path']}`")
            out.append("")
            meta_line = (f"`{e['kind']}` · {e['lines']} lines · {e['bytes']:,} B · "
                         f"description: **{src}**")
            out.append(meta_line)
            out.append("")
            out.append(f"**Purpose.** {purpose}")
            out.append("")
            if contents:
                out.append(f"**Contents.** {contents}")
                out.append("")
            out.append(f"**Use.** {use}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stdout", action="store_true", help="print instead of writing")
    args = ap.parse_args(argv)
    if not INDEX_JSON.exists():
        sys.exit("index/INDEX.json is missing. Run: python3 index/build.py all")
    meta = json.loads(INDEX_JSON.read_text())
    text = render(meta)
    if args.stdout:
        print(text)
        return 0
    DEST.parent.mkdir(exist_ok=True)
    DEST.write_text(text)
    n_cur = sum(1 for e in meta["files"] if e["path"] in CURATED)
    missing = [e["path"] for e in meta["files"]
               if not e["summary"] and e["path"] not in CURATED]
    print(f"{DEST.relative_to(REPO)}: {meta['counts']['files']} files "
          f"({n_cur} curated), {len(text.splitlines()):,} lines")
    if missing:
        print(f"  {len(missing)} files have neither a summary nor a CURATED entry:")
        for m in missing:
            print(f"    {m}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

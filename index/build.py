"""Build the searchable indexes over every tracked file in this repository.

    python3 index/build.py all          # metadata + text + concepts (no network)
    python3 index/build.py semantic     # embeddings; needs a local ollama (opt-in)
    python3 index/build.py --check      # exit 1 if the index is stale vs the tree

Four indexes, three of them committed:

| Artifact | What it answers | Committed |
|---|---|---|
| `index/INDEX.json` | "what files exist, and what is each one" | yes |
| `index/TEXT-INDEX.json` | "which files contain this word" (BM25) | yes |
| `index/CONCEPT-INDEX.json` | "which files bear on this idea" | yes |
| `index/semantic-embeddings.npz` | "which files mean something like this" | **no** |

**Why the embeddings are gitignored.** They are ~1500 chunks x 1024 float16, a
few MB of derived binary that re-diffs on every content change, in a repo whose
entire tracked source tree is a few MB. `data/` is gitignored for the same
reason. What is
committed is `index/SEMANTIC-MANIFEST.json`, which records the model, dimensions,
chunk count and per-file source hashes, so a reader can tell what the index *was*
and whether it would still be valid. `search.py --semantic` refuses with the
rebuild command when the array is absent.

**Network.** `AGENTS.md` and `CLAUDE.md` require that the backtest engine never
touches the network, and it does not: this is tooling, it lives outside
`backtester/`, nothing under `backtester/` imports it (there is a test asserting
that), and only the opt-in `semantic` subcommand talks to anything — `localhost`
ollama, never a remote host. `all` is deliberately offline.

**Staleness is the real risk.** An index looks authoritative and goes stale
silently on every commit. This repo has twice been bitten by result files nobody
could re-derive, so `--check` re-hashes the tree and exits non-zero listing what
was added, removed or changed. Run it before trusting the index, and in CI.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "index"
SCHEMA_VERSION = 1

INDEX_JSON = OUT / "INDEX.json"
TEXT_JSON = OUT / "TEXT-INDEX.json"
CONCEPT_JSON = OUT / "CONCEPT-INDEX.json"
SEMANTIC_NPZ = OUT / "semantic-embeddings.npz"
SEMANTIC_MANIFEST = OUT / "SEMANTIC-MANIFEST.json"

# Extensions worth reading as text. Anything else is recorded in INDEX.json with
# metadata but contributes no tokens and no embedding — an .icns file has a size
# and a purpose but no searchable content.
TEXT_EXT = {".py", ".md", ".js", ".json", ".txt", ".csv", ".yml", ".yaml",
            ".html", ".css", ".editorconfig", ".gitignore", ""}

# CSV bodies are excluded from the text and semantic indexes on purpose. A
# 2,000-row price file would dominate every token count with numerals and teach
# the index nothing; its *header* and shape are the searchable facts.
BODY_EXCLUDED_EXT = {".csv"}

# The index's own output, excluded from the index entirely. Including it tripled
# the token count and made `--check` unsatisfiable: every build rewrote a file the
# build had just hashed, so the index was stale the instant it was written. The
# generators under index/ ARE indexed — they are source.
SELF_EXCLUDED = {
    "index/INDEX.json",
    "index/TEXT-INDEX.json",
    "index/CONCEPT-INDEX.json",
    "index/SEMANTIC-MANIFEST.json",
}

# Tracked and searchable, but generated FROM the index, so they cannot be inputs
# to it. They are indexed (a reader searches them like any other prose) and
# excluded from the staleness hash, because "the index is stale" has to mean the
# *source* moved — not that a derived document was rewritten a second later.
DERIVED_TRACKED = {
    "docs/FILES.md",
    "docs/CONCEPTS.md",
}

EMBED_MODEL = "mxbai-embed-large"
EMBED_URL = "http://localhost:11434/api/embed"
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "not", "are", "but", "was", "has",
    "from", "its", "it", "is", "of", "to", "in", "on", "as", "at", "by", "an", "a",
    "be", "or", "if", "so", "no", "do", "we", "you", "can", "will", "which", "than",
    "then", "them", "they", "there", "their", "what", "when", "how", "why", "all",
    "any", "one", "two", "more", "most", "some", "such", "only", "same", "other",
    "into", "over", "under", "each", "per", "out", "up", "down", "would", "could",
    "should", "may", "might", "must", "have", "had", "been", "being", "were", "does",
    "did", "done", "here", "where", "who", "whom", "whose", "because", "while",
    "about", "after", "before", "between", "both", "during", "against", "above",
    "below", "further", "once", "very", "just", "also", "even", "still", "yet",
    "self", "none", "true", "false", "def", "class", "import", "return", "print",
}


# ---------------------------------------------------------------------------
# Tree walk
# ---------------------------------------------------------------------------

def tracked_files() -> list[str]:
    """Every file git tracks, which is the definition of "in the repo".

    Deliberately not a filesystem walk: `data/` and the embeddings are gitignored
    precisely because they are derived, and an index that included them would
    index its own output and a price cache that differs per machine.
    """
    r = subprocess.run(["git", "-C", str(REPO), "ls-files"],
                       capture_output=True, text=True, check=True)
    return sorted(x for x in r.stdout.splitlines()
                  if x.strip() and x not in SELF_EXCLUDED)


def sha1_of(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def classify(rel: str) -> str:
    """One coarse `kind` per file, chosen to match how someone searches.

    Ordering matters: a test *is* Python, a strategy card *is* markdown, and the
    more specific answer is the useful one.
    """
    p = Path(rel)
    ext = p.suffix
    parts = p.parts
    if "tests" in parts or p.name.startswith("test_"):
        return "test"
    if "strategy_cards" in parts:
        return "strategy-card"
    if "results" in parts:
        return "result"
    if "coin-intelligence" in parts:
        return "coin-reference"
    if parts[0] == "docs":
        return "doc"
    if parts[0] == ".github":
        return "ci"
    if ext == ".py":
        return "code-python"
    if ext == ".js":
        return "code-js"
    if ext in {".html", ".css"}:
        return "code-web"
    if ext == ".md":
        return "doc"
    if ext in {".json", ".yml", ".yaml", ".editorconfig", ".gitignore"}:
        return "config"
    if ext in {".csv", ".txt"}:
        return "data"
    return "other"


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return ""


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Flat YAML frontmatter, without taking a YAML dependency.

    Only scalar `key: value` pairs at the top level are read, which is all the
    strategy cards and coin spokes use for the fields worth indexing. Nested
    blocks are skipped rather than guessed at.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict[str, Any] = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if m and m.group(2).strip():
            out[m.group(1)] = m.group(2).strip().strip("\"'")
    return out


def first_paragraph(s: str, limit: int = 400) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    dot = cut.rfind(". ")
    return (cut[: dot + 1] if dot > limit // 3 else cut).strip()


def python_facts(text: str) -> tuple[str, list[str], list[str]]:
    """(module docstring, top-level symbols, imported modules)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return "", [], []
    doc = ast.get_docstring(tree) or ""
    syms: list[str] = []
    imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            syms.append(f"{node.name}()")
        elif isinstance(node, ast.ClassDef):
            syms.append(f"class {node.name}")
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.isupper():
                    syms.append(t.id)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return doc, syms, sorted(imports)


def js_docstring(text: str) -> str:
    """The leading JSDoc block, or a run of `//` lines at the top of the file.

    Worth extracting rather than curating: nearly every JS file here opens with a
    substantial `/** ... */` header of the same quality as the Python module
    docstrings, so this lifts JS summary coverage from nothing to near-complete.
    The exceptions are the three `extension/test/*.test.js` files, which open with
    imports and are covered by CURATED entries in make_files_doc.py instead.
    """
    # A shebang precedes the JSDoc in the executable tools, so skip one if present.
    text = re.sub(r"^#![^\n]*\n", "", text, count=1)
    m = re.match(r"\s*/\*\*(.*?)\*/", text, re.S)
    if m:
        lines = [re.sub(r"^\s*\*\s?", "", ln) for ln in m.group(1).splitlines()]
        return " ".join(ln.strip() for ln in lines if ln.strip())
    run: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("//"):
            run.append(s.lstrip("/").strip())
        elif run or s:
            break
    return " ".join(run)


def csv_summary(rel: str, header: list[str], rows: int) -> str:
    """A derived one-liner for a generated data file.

    Prose per result CSV would be invented; the honest summary is its shape. These
    are labelled `derived` in `summarySource` so a reader can tell them apart from
    something an author wrote.
    """
    if not header:
        return ""
    cols = ", ".join(header[:8]) + ("..." if len(header) > 8 else "")
    return f"Generated data: {rows} rows x {len(header)} columns ({cols})."


def js_symbols(text: str) -> list[str]:
    syms = re.findall(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)",
                      text, re.M)
    syms += [f"class {x}" for x in re.findall(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)",
                                             text, re.M)]
    syms += re.findall(r"^\s*(?:export\s+)?const\s+([A-Z][A-Z0-9_]{2,})\s*=", text, re.M)
    return sorted(set(syms))


def md_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def summarise(rel: str, text: str, fm: dict[str, Any], doc: str) -> str:
    """The one-line answer to "what is this file". Extraction only; no invention.

    Priority is by reliability: an author-written `summary`/`description` beats a
    module docstring, which beats the opening prose, which beats nothing. The
    caller records which source won so `docs/FILES.md` can label it.
    """
    for key in ("summary", "description"):
        if fm.get(key):
            return first_paragraph(str(fm[key]))
    if doc:
        return first_paragraph(doc)
    if rel.endswith(".md"):
        body = text.split("\n---", 1)[-1] if text.startswith("---") else text
        prose = [ln.strip() for ln in body.splitlines()
                 if ln.strip() and not ln.startswith(("#", ">", "|", "-", "*", "`", "["))]
        if prose:
            return first_paragraph(" ".join(prose[:3]))
    return ""


def summary_source(fm: dict[str, Any], doc: str, summary: str) -> str:
    if not summary:
        return "none"
    if fm.get("summary") or fm.get("description"):
        return "frontmatter"
    if doc:
        return "docstring"
    return "opening-prose"


def build_meta() -> dict[str, Any]:
    entries = []
    for rel in tracked_files():
        p = REPO / rel
        if not p.is_file():
            continue
        ext = p.suffix
        raw = read_text(p) if ext in TEXT_EXT else ""
        fm = parse_frontmatter(raw) if ext == ".md" else {}
        doc, syms, imports = python_facts(raw) if ext == ".py" else ("", [], [])
        if ext == ".js":
            syms = js_symbols(raw)
            doc = js_docstring(raw)
        summary = summarise(rel, raw, fm, doc)
        # Generated artifacts get a summary derived from their shape rather than
        # prose someone would have to invent. Labelled `derived` in summarySource.
        derived = False
        if not summary and ext == ".csv":
            head = raw.splitlines()[:1]
            summary = csv_summary(rel, head[0].split(",") if head else [],
                                  max(0, raw.count("\n") - 1))
            derived = bool(summary)
        elif not summary and ext == ".json" and raw.strip():
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    ks = list(obj)
                    summary = (f"Generated JSON object, {len(ks)} keys "
                               f"({', '.join(map(str, ks[:6]))}"
                               f"{'...' if len(ks) > 6 else ''}).")
                elif isinstance(obj, list):
                    summary = f"Generated JSON array, {len(obj)} entries."
                derived = bool(summary)
            except ValueError:
                pass
        elif not summary and ext == ".txt" and raw.strip():
            head = [ln.strip() for ln in raw.splitlines() if ln.strip()][:2]
            if head:
                summary = f"Generated report. Opens: {' / '.join(head)}"[:300]
                derived = True
        title = fm.get("name") or md_title(raw) or Path(rel).stem
        internal = sorted(m for m in imports
                          if m in {"backtester", "research", "soltui", "index"})
        entry = {
            "id": rel,
            "path": rel,
            "dir": str(Path(rel).parent) if str(Path(rel).parent) != "." else "",
            "name": Path(rel).name,
            "ext": ext,
            "kind": classify(rel),
            "title": title,
            "summary": summary,
            "summarySource": "derived" if derived else summary_source(fm, doc, summary),
            "bytes": p.stat().st_size,
            "lines": raw.count("\n") + 1 if raw else 0,
            "sha1": sha1_of(p),
            "symbols": syms[:40],
            "imports": imports,
            "internalImports": internal,
            "frontmatter": fm,
        }
        if ext == ".csv":
            head = raw.splitlines()[:1]
            entry["csvHeader"] = head[0].split(",") if head else []
            entry["csvRows"] = max(0, raw.count("\n") - 1)
        entries.append(entry)

    kinds = Counter(e["kind"] for e in entries)
    dirs = Counter(e["dir"].split("/")[0] or "(root)" for e in entries)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schemaVersion": SCHEMA_VERSION,
        "repoRoot": "~/dev/solmargintrader",
        "commit": subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "counts": {
            "files": len(entries),
            "bytes": sum(e["bytes"] for e in entries),
            "byKind": dict(sorted(kinds.items(), key=lambda x: -x[1])),
            "byTopDir": dict(sorted(dirs.items(), key=lambda x: -x[1])),
            "withSummary": sum(1 for e in entries if e["summary"]),
        },
        "files": entries,
    }


# ---------------------------------------------------------------------------
# Text index (BM25 postings)
# ---------------------------------------------------------------------------

def tokenize(s: str) -> list[str]:
    toks = re.findall(r"[a-z][a-z0-9_]{2,}", s.lower())
    return [t for t in toks if t not in STOPWORDS]


def build_text(meta: dict[str, Any]) -> dict[str, Any]:
    """Inverted index with term frequencies, ready for BM25 in `search.py`.

    Scoring lives in the searcher, not here: the index stores counts, which do not
    change when someone tunes k1/b. Identifier tokens are split as well as kept
    whole (`cpcv_evaluate` yields `cpcv_evaluate`, `cpcv`, `evaluate`) so a search
    for a concept finds the function named after it.
    """
    postings: dict[str, dict[str, int]] = defaultdict(dict)
    lengths: dict[str, int] = {}
    for e in meta["files"]:
        p = REPO / e["path"]
        body = "" if e["ext"] in BODY_EXCLUDED_EXT else read_text(p)
        searchable = " ".join([
            e["path"].replace("/", " ").replace("_", " ").replace("-", " "),
            e["title"], e["summary"], " ".join(e["symbols"]),
            " ".join(e.get("csvHeader", [])), body,
        ])
        toks = tokenize(searchable)
        extra: list[str] = []
        for t in toks:
            if "_" in t:
                extra.extend(x for x in t.split("_") if len(x) > 2)
        toks += extra
        if not toks:
            lengths[e["id"]] = 0
            continue
        tf = Counter(toks)
        lengths[e["id"]] = len(toks)
        for term, n in tf.items():
            postings[term][e["id"]] = n

    # Terms in almost every file carry no discriminating power and inflate the
    # artifact; terms in exactly one file are usually a typo or a hash.
    n_docs = len(lengths)
    pruned = {t: d for t, d in postings.items() if len(d) <= n_docs * 0.6}
    return {
        "generatedAt": meta["generatedAt"],
        "schemaVersion": SCHEMA_VERSION,
        "stats": {
            "documents": n_docs,
            "terms": len(pruned),
            "termsBeforePrune": len(postings),
            "totalTokens": sum(lengths.values()),
            "avgDocLength": round(sum(lengths.values()) / max(1, n_docs), 1),
        },
        "docLengths": lengths,
        "postings": {t: dict(sorted(d.items())) for t, d in sorted(pruned.items())},
    }


# ---------------------------------------------------------------------------
# Concept index
# ---------------------------------------------------------------------------

# Concepts come from the repo's own vocabulary, not an invented taxonomy: the
# `FAMILY` dict in backtester/core/strategies, the strategy-card frontmatter keys,
# docs/trading-signals-concept-family.md, and the terms that actually recur across
# the corpus. Every concept is verified to match at least one file before it is
# written, and one that matches nothing is dropped rather than kept for tidiness.
CONCEPTS: dict[str, dict[str, Any]] = {
    "cpcv": {
        "label": "Combinatorial purged cross-validation",
        "why": "The repo's primary evaluation method: 8 blocks, k=2, up to 28 paths. "
               "Replaced the single 70/30 split, whose in-sample window ended on the "
               "highest close in the series.",
        "terms": ["cpcv", "purged", "combinatorial", "n_groups", "k_test", "path_sharpes"],
    },
    "overfitting-pbo": {
        "label": "Overfitting and PBO",
        "why": "PBO measured 0.700 at daily horizons against a 0.500 noise line, so "
               "in-sample rank is anti-informative. This is the finding that governs "
               "how every other number here may be read.",
        "terms": ["pbo", "overfitting", "cscv", "deflated", "anti-informative",
                  "multiple-testing"],
    },
    "lookahead": {
        "label": "Lookahead and fill timing",
        "why": "A signal at bar t may use data only through t. Centred indicators, "
               "same-bar fills and displaced clouds are the recurring hazards.",
        "terms": ["lookahead", "fill_delay", "warmup", "warmup_bars", "displacement",
                  "centred", "shift"],
    },
    "costs": {
        "label": "Cost model",
        "why": "Fees and slippage are never optional and must be applied exactly once. "
               "The engine runs fee_bps=6.0, slippage_bps=2.0, fill_delay=1.",
        "terms": ["fee_bps", "slippage", "slippage_bps", "costconfig", "break-even",
                  "borrow", "financing"],
    },
    "evidence-floor": {
        "label": "Evidence floor",
        "why": "Below a minimum trade count a result is not eligible to be reported as "
               "an improvement. cpcv_evaluate prints DROPPED but still returns paths, "
               "which is how a 6-trade Sharpe reached a headline.",
        "terms": ["min_total_trades", "min_rankable_trades", "insufficient", "dropped",
                  "evidence floor", "rankable"],
    },
    "robustness": {
        "label": "Perturbation and robustness",
        "why": "Second independent axis beside CPCV: nudge each parameter +/-10% and "
               "re-run. A point that collapses is a spike, not a plateau.",
        "terms": ["perturb", "perturbation", "ratio_to_iqr", "sign_flips", "stability"],
    },
    "transfer": {
        "label": "Cross-asset and cross-timeframe transfer",
        "why": "The same 25 strategies score 25/25 on BTC daily and 0/25 on SOL hourly. "
               "The dataset has repeatedly explained more than the strategy.",
        "terms": ["cross_asset", "cross-asset", "transfer", "doge", "zec", "universe",
                  "top_coins"],
    },
    "benchmark": {
        "label": "Buy-and-hold benchmark",
        "why": "Zero parameters, and it out-ranked all but one or two strategies on SOL "
               "and all five recommended configurations on ZEC.",
        "terms": ["buy_and_hold", "benchmark", "baseline"],
    },
    "execution-onchain": {
        "label": "On-chain execution reality",
        "why": "Oracle-priced perps, priority fees as a product, per-account fee "
               "markets, dropped-versus-reverted. Decides whether a strategy is "
               "executable at all.",
        "terms": ["jupiter", "jlp", "oracle", "priority", "slippage", "perps", "solana"],
    },
    "risk-rails": {
        "label": "Risk rails and dry-run safety",
        "why": "The extension can place real orders. Dry-run is the default, rails live "
               "in code and fail closed, and a fresh install must never be able to trade.",
        "terms": ["dry_run", "dryrun", "risk", "rails", "kill", "guard", "confirm",
                  "fail-closed"],
    },
    "grid": {
        "label": "Grid trading",
        "why": "A resting grid converts a sustained trend into a maximum-size losing "
               "position; the re-centring gate fired once in 1,875 bars.",
        "terms": ["grid", "gridsim", "ladder", "recenter", "anchor_window", "levels"],
    },
    "data-integrity": {
        "label": "Data integrity",
        "why": "Gaps refused rather than filled, columns resolved by name, timestamps "
               "monotone. A concatenated XRP series hides a 2.5-year join.",
        "terms": ["validate_bars", "strict_gaps", "allow_gaps", "datavalidationerror",
                  "monotone", "gap"],
    },
}

# Concepts drawn straight from the repo's own strategy taxonomy.
FAMILY_CONCEPT_TERMS = {
    "trend": ["trend", "ma_crossover", "macd", "ichimoku"],
    "breakout": ["breakout", "bb_breakout", "keltner"],
    "mean-reversion": ["mean-reversion", "zscore", "bb_reversion", "vwap_reversion",
                       "ou_reversion"],
    "momentum": ["momentum", "ts_momentum", "dual_momentum"],
    "regime-filter": ["regime", "sma_regime", "adx_trend", "hurst", "vol_regime"],
    "risk-overlay": ["voltarget", "atr_sized", "garch", "risk-overlay"],
    "oscillator-reversion": ["rsi", "stochastic", "oscillator"],
    "volume-flow": ["obv", "volume-flow"],
    "baseline": ["buy_and_hold", "baseline"],
}


def build_concepts(meta: dict[str, Any], text: dict[str, Any]) -> dict[str, Any]:
    postings = text["postings"]

    TOP_N = 30

    def files_for(terms: list[str]) -> tuple[int, list[dict[str, Any]]]:
        """(total files matching, the strongest TOP_N of them).

        The total is returned separately because truncating the list and then
        reporting its length made every concept claim exactly 30 files — a count
        that described the truncation rather than the corpus.
        """
        hits: Counter[str] = Counter()
        for t in terms:
            for fid, n in postings.get(t.lower(), {}).items():
                hits[fid] += n
        return len(hits), [{"path": f, "hits": n} for f, n in hits.most_common(TOP_N)]

    concepts = []
    dropped = []
    for cid, spec in CONCEPTS.items():
        total, files = files_for(spec["terms"])
        if not files:
            dropped.append(cid)
            continue
        concepts.append({
            "id": cid, "label": spec["label"], "why": spec["why"],
            "terms": spec["terms"], "matchingFiles": total,
            "shown": len(files), "files": files,
            "source": "curated-from-repo-vocabulary",
        })

    for fam, terms in FAMILY_CONCEPT_TERMS.items():
        total, files = files_for(terms)
        if not files:
            dropped.append(f"family:{fam}")
            continue
        concepts.append({
            "id": f"family:{fam}",
            "label": f"Strategy family: {fam}",
            "why": "A value of the FAMILY dict in backtester/core/strategies/__init__.py, "
                   "which is the repo's own taxonomy rather than one imposed here.",
            "terms": terms, "matchingFiles": total,
            "shown": len(files), "files": files,
            "source": "backtester/core/strategies/__init__.py FAMILY",
        })

    # Card statuses and families are facts already written in the cards.
    card_axes: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for e in meta["files"]:
        fm = e.get("frontmatter") or {}
        for axis in ("status", "family", "success_likelihood", "evaluation"):
            if fm.get(axis):
                card_axes[axis][str(fm[axis])].append(e["path"])

    return {
        "generatedAt": meta["generatedAt"],
        "schemaVersion": SCHEMA_VERSION,
        "note": "Concepts are derived from the repo's own vocabulary — the FAMILY dict, "
                "strategy-card frontmatter, docs/trading-signals-concept-family.md, and "
                "terms verified to recur in the corpus. A concept matching no file is "
                "dropped, not kept.",
        "counts": {"concepts": len(concepts), "dropped": len(dropped)},
        "droppedForNoMatches": dropped,
        "concepts": sorted(concepts, key=lambda c: -c["matchingFiles"]),
        "cardAxes": {k: {kk: sorted(vv) for kk, vv in sorted(v.items())}
                     for k, v in sorted(card_axes.items())},
    }


# ---------------------------------------------------------------------------
# Semantic index (opt-in; localhost ollama only)
# ---------------------------------------------------------------------------

def chunks_of(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    out = []
    step = CHUNK_CHARS - CHUNK_OVERLAP
    for i in range(0, len(text), step):
        piece = text[i:i + CHUNK_CHARS].strip()
        if len(piece) > 80:
            out.append(piece)
        if i + CHUNK_CHARS >= len(text):
            break
    return out


def embed(inputs: list[str]) -> list[list[float]]:
    body = json.dumps({"model": EMBED_MODEL, "input": inputs}).encode()
    req = urllib.request.Request(EMBED_URL, data=body,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    return d.get("embeddings") or [d["embedding"]]


def build_semantic(meta: dict[str, Any]) -> int:
    try:
        import numpy as np
    except ImportError:
        print("SEMANTIC BUILD SKIPPED: numpy is required.")
        return 1

    texts: list[str] = []
    owners: list[str] = []
    for e in meta["files"]:
        if e["ext"] in BODY_EXCLUDED_EXT or e["ext"] not in TEXT_EXT:
            continue
        raw = read_text(REPO / e["path"])
        header = f"{e['path']} — {e['title']}. {e['summary']}\n"
        for c in chunks_of(raw):
            texts.append(header + c)
            owners.append(e["path"])
    if not texts:
        print("SEMANTIC BUILD SKIPPED: nothing to embed.")
        return 1

    print(f"Embedding {len(texts)} chunks from "
          f"{len(set(owners))} files with {EMBED_MODEL} at {EMBED_URL} ...")
    vecs: list[list[float]] = []
    BATCH = 32
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i + BATCH]
        try:
            vecs.extend(embed(batch))
        except (urllib.error.URLError, OSError, KeyError) as exc:
            print(f"SEMANTIC BUILD FAILED at chunk {i}: {exc}")
            print(f"  Is ollama running, and is `{EMBED_MODEL}` pulled? "
                  f"`ollama pull {EMBED_MODEL}`")
            return 1
        print(f"  {min(i + BATCH, len(texts))}/{len(texts)}", end="\r", flush=True)
    print()

    arr = np.asarray(vecs, dtype="float32")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    arr = (arr / norms).astype("float16")   # pre-normalised: cosine becomes a dot product
    # Only the float matrix goes in the .npz. The chunk-to-file mapping lives in the
    # committed manifest instead, which means `np.load` never needs
    # `allow_pickle=True` — loading a pickled object array is arbitrary code
    # execution, and an index that a reader may fetch or regenerate is exactly the
    # wrong place for that. It also makes the mapping inspectable without numpy.
    np.savez_compressed(SEMANTIC_NPZ, embeddings=arr)

    SEMANTIC_MANIFEST.write_text(json.dumps({
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schemaVersion": SCHEMA_VERSION,
        "model": EMBED_MODEL,
        "endpoint": EMBED_URL,
        "dims": arr.shape[1],
        "chunks": int(arr.shape[0]),
        "files": len(set(owners)),
        "chunkChars": CHUNK_CHARS,
        "chunkOverlap": CHUNK_OVERLAP,
        "dtype": "float16, L2-normalised (cosine == dot product)",
        "arrayFile": SEMANTIC_NPZ.name,
        "arrayCommitted": False,
        "chunkOwners": owners,
        "note": "The array is gitignored: derived, a few MB, and it re-diffs on every "
                "content change. This manifest records what the index was; rebuild with "
                "`python3 index/build.py semantic`.",
        "sourceSha1": {e["path"]: e["sha1"] for e in meta["files"]
                       if e["path"] in set(owners)},
    }, indent=2) + "\n")
    print(f"Wrote {SEMANTIC_NPZ.relative_to(REPO)} "
          f"({SEMANTIC_NPZ.stat().st_size / 1e6:.1f} MB, gitignored) "
          f"and {SEMANTIC_MANIFEST.relative_to(REPO)}")
    return 0


# ---------------------------------------------------------------------------
# Staleness gate
# ---------------------------------------------------------------------------

def check() -> int:
    """Compare the committed index against the tree. Exit 1 on any drift.

    This is the guard the repo learned to want: two result files here could not be
    re-derived, and one of them was wrong in a way that survived because nothing
    re-hashed it. An index is the same failure class with a friendlier face.
    """
    if not INDEX_JSON.exists():
        print(f"INDEX CHECK FAILED: {INDEX_JSON.relative_to(REPO)} does not exist.")
        print("  Build it: python3 index/build.py all")
        return 1
    old = json.loads(INDEX_JSON.read_text())
    was = {e["path"]: e["sha1"] for e in old["files"]
           if e["path"] not in DERIVED_TRACKED}
    now = {rel: sha1_of(REPO / rel) for rel in tracked_files()
           if (REPO / rel).is_file() and rel not in DERIVED_TRACKED}

    added = sorted(set(now) - set(was))
    removed = sorted(set(was) - set(now))
    changed = sorted(p for p in set(was) & set(now) if was[p] != now[p])

    if not (added or removed or changed):
        print(f"INDEX CHECK PASSED: {len(now)} source files, all hashes match "
              f"(index built at {old['generatedAt']}, commit {old.get('commit')}).")
        print(f"  Excluded from the hash: {len(DERIVED_TRACKED)} derived docs "
              f"({', '.join(sorted(DERIVED_TRACKED))}) and the index's own output.")
        return 0
    print("INDEX CHECK FAILED: the index is stale.")
    for label, items in (("added", added), ("removed", removed), ("changed", changed)):
        if items:
            print(f"  {len(items)} {label}:")
            for x in items[:12]:
                print(f"    {x}")
            if len(items) > 12:
                print(f"    ... and {len(items) - 12} more")
    print("  Rebuild: python3 index/build.py all")
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", nargs="?", default="all",
                    choices=["all", "meta", "text", "concepts", "semantic"])
    ap.add_argument("--check", action="store_true",
                    help="verify the committed index matches the tree; exit 1 if stale")
    args = ap.parse_args(argv)

    if args.check:
        return check()

    OUT.mkdir(exist_ok=True)
    meta = build_meta()

    if args.command == "semantic":
        return build_semantic(meta)

    if args.command in {"all", "meta"}:
        INDEX_JSON.write_text(json.dumps(meta, indent=2) + "\n")
        c = meta["counts"]
        print(f"{INDEX_JSON.relative_to(REPO)}: {c['files']} files, "
              f"{c['bytes'] / 1e6:.1f} MB, {c['withSummary']} with a summary")

    if args.command in {"all", "text", "concepts"}:
        text = build_text(meta)
        if args.command in {"all", "text"}:
            TEXT_JSON.write_text(json.dumps(text, indent=2, sort_keys=True) + "\n")
            s = text["stats"]
            print(f"{TEXT_JSON.relative_to(REPO)}: {s['terms']} terms "
                  f"(pruned from {s['termsBeforePrune']}), "
                  f"{s['totalTokens']} tokens, avg doc {s['avgDocLength']}")
        if args.command in {"all", "concepts"}:
            con = build_concepts(meta, text)
            CONCEPT_JSON.write_text(json.dumps(con, indent=2) + "\n")
            print(f"{CONCEPT_JSON.relative_to(REPO)}: {con['counts']['concepts']} concepts"
                  + (f", {con['counts']['dropped']} dropped for no matches"
                     if con["counts"]["dropped"] else ""))

    if args.command == "all":
        print("\nSemantic index is opt-in and needs a local ollama:")
        print("  python3 index/build.py semantic")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

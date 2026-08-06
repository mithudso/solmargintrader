"""Search the repository index: keyword, meaning, or concept.

    python3 index/search.py "how are costs applied"          # hybrid
    python3 index/search.py --text "purged cross validation"  # BM25, exact terms
    python3 index/search.py --semantic "why did the strategy stop working"
    python3 index/search.py --concept evidence-floor
    python3 index/search.py --concepts                       # list every concept
    python3 index/search.py --file backtester/core/cpcv.py    # one file's entry
    python3 index/search.py --kind code-python "grid"         # filter by kind

Three retrieval modes, because they fail differently:

- **text** (BM25 over `TEXT-INDEX.json`) is exact and explainable. It finds
  `fee_bps` and cannot find "how much does trading cost".
- **semantic** (cosine over `semantic-embeddings.npz`) finds paraphrase and cannot
  be trusted on an identifier — an embedding will happily rank `slippage_bps` near
  `fee_bps` when you wanted one of them specifically.
- **hybrid** (default) runs both and fuses the ranks, which is the right default
  precisely because a reader rarely knows which kind of query they are typing.

Semantic requires the gitignored array. If it is absent, hybrid degrades to text
and says so rather than silently returning worse results.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "index"
INDEX_JSON = OUT / "INDEX.json"
TEXT_JSON = OUT / "TEXT-INDEX.json"
CONCEPT_JSON = OUT / "CONCEPT-INDEX.json"
SEMANTIC_NPZ = OUT / "semantic-embeddings.npz"
SEMANTIC_MANIFEST = OUT / "SEMANTIC-MANIFEST.json"

BM25_K1 = 1.2
BM25_B = 0.75
RRF_K = 60  # Reciprocal-rank-fusion constant; 60 is the value from the original paper.


def load(path: Path, what: str) -> dict:
    if not path.exists():
        sys.exit(f"{path.relative_to(REPO)} is missing. Build it: python3 index/build.py all\n"
                 f"  ({what})")
    return json.loads(path.read_text())


def tokenize(s: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9_]{2,}", s.lower())


def bm25(query: str, text: dict) -> list[tuple[str, float]]:
    """Standard BM25 over the committed postings.

    Scoring lives here rather than in the index so that tuning k1/b never requires
    a rebuild, and so the index stays a statement of fact (counts) rather than of
    preference (weights).
    """
    postings = text["postings"]
    lengths = text["docLengths"]
    n = max(1, len(lengths))
    avgdl = text["stats"]["avgDocLength"] or 1.0
    terms = tokenize(query)
    # An identifier like `fee_bps` is also worth matching on its parts, the same
    # split the builder applied, or a query typed with underscores would miss the
    # prose that discusses it.
    for t in list(terms):
        if "_" in t:
            terms.extend(p for p in t.split("_") if len(p) > 2)

    scores: dict[str, float] = {}
    for t in set(terms):
        d = postings.get(t)
        if not d:
            continue
        df = len(d)
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        for fid, tf in d.items():
            dl = lengths.get(fid, 0) or 1
            denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl)
            scores[fid] = scores.get(fid, 0.0) + idf * (tf * (BM25_K1 + 1)) / denom
    return sorted(scores.items(), key=lambda x: -x[1])


def semantic(query: str, limit: int = 40) -> list[tuple[str, float]] | None:
    """Cosine similarity over chunk embeddings, best chunk per file.

    Returns None (rather than raising) when the array is absent, so hybrid can
    degrade to text and say so. Per-file score is the max over its chunks: a long
    document that answers the query in one paragraph should rank on that
    paragraph, not be diluted by the rest of itself.
    """
    if not SEMANTIC_NPZ.exists():
        return None
    try:
        import numpy as np
        import urllib.request
    except ImportError:
        return None
    man = json.loads(SEMANTIC_MANIFEST.read_text()) if SEMANTIC_MANIFEST.exists() else {}
    model = man.get("model", "mxbai-embed-large")
    url = man.get("endpoint", "http://localhost:11434/api/embed")
    try:
        body = json.dumps({"model": model, "input": [query]}).encode()
        req = urllib.request.Request(url, data=body,
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
        q = np.asarray((d.get("embeddings") or [d["embedding"]])[0], dtype="float32")
    except Exception as exc:  # noqa: BLE001 - any transport failure degrades to text
        print(f"  (semantic unavailable: {type(exc).__name__}; is ollama running?)")
        return None
    q /= (np.linalg.norm(q) or 1.0)

    owners = man.get("chunkOwners") or []
    if not owners:
        print("  (semantic manifest has no chunkOwners; rebuild: "
              "python3 index/build.py semantic)")
        return None
    # No `allow_pickle`: the array holds only floats, and the chunk-to-file mapping
    # comes from the committed manifest. Unpickling an array is arbitrary code
    # execution, which is not a risk an index should carry.
    z = np.load(SEMANTIC_NPZ)
    emb = z["embeddings"].astype("float32")   # already L2-normalised at build time
    if len(owners) != emb.shape[0]:
        print(f"  (semantic index is stale: {emb.shape[0]} vectors vs "
              f"{len(owners)} owners; rebuild: python3 index/build.py semantic)")
        return None
    sims = emb @ q
    best: dict[str, float] = {}
    for owner, s in zip(owners, sims):
        f = str(owner)
        if s > best.get(f, -2.0):
            best[f] = float(s)
    return sorted(best.items(), key=lambda x: -x[1])[:limit]


def fuse(a: list[tuple[str, float]], b: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Reciprocal rank fusion. Ranks combine; raw scores are not comparable.

    A BM25 score and a cosine similarity live on different scales, so averaging
    them would let whichever happens to be larger dominate. RRF only uses position.
    """
    out: dict[str, float] = {}
    for lst in (a, b):
        for i, (fid, _) in enumerate(lst):
            out[fid] = out.get(fid, 0.0) + 1.0 / (RRF_K + i + 1)
    return sorted(out.items(), key=lambda x: -x[1])


def show(hits: list[tuple[str, float]], meta: dict, limit: int, label: str,
         kind: str | None) -> None:
    by_id = {e["id"]: e for e in meta["files"]}
    if kind:
        hits = [(f, s) for f, s in hits if by_id.get(f, {}).get("kind") == kind]
    if not hits:
        print("No matches.")
        return
    print(f"{label} — top {min(limit, len(hits))} of {len(hits)}\n")
    for fid, score in hits[:limit]:
        e = by_id.get(fid)
        if not e:
            continue
        print(f"  {score:6.3f}  {e['path']}")
        print(f"          [{e['kind']}] {e['lines']} lines, {e['bytes']:,} B"
              + (f", {len(e['symbols'])} symbols" if e["symbols"] else ""))
        if e["summary"]:
            s = e["summary"]
            print(f"          {s[:200]}{'...' if len(s) > 200 else ''}"
                  f"  ({e['summarySource']})")
        print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("query", nargs="*", help="free text")
    ap.add_argument("--text", action="store_true", help="BM25 only")
    ap.add_argument("--semantic", action="store_true", help="embeddings only")
    ap.add_argument("--concept", metavar="ID", help="files bearing on one concept")
    ap.add_argument("--concepts", action="store_true", help="list every concept")
    ap.add_argument("--file", metavar="PATH", help="show one file's index entry")
    ap.add_argument("--kind", metavar="KIND", help="restrict to a kind, e.g. code-python")
    ap.add_argument("-n", "--limit", type=int, default=10)
    args = ap.parse_args(argv)

    meta = load(INDEX_JSON, "the file metadata index")

    if args.concepts:
        con = load(CONCEPT_JSON, "the concept index")
        print(f"{con['counts']['concepts']} concepts "
              f"(derived from the repo's own vocabulary)\n")
        for c in con["concepts"]:
            print(f"  {c['id']:26s} {c['matchingFiles']:3d} files  {c['label']}")
        print("\nDetail: python3 index/search.py --concept <id>")
        return 0

    if args.concept:
        con = load(CONCEPT_JSON, "the concept index")
        m = next((c for c in con["concepts"] if c["id"] == args.concept), None)
        if not m:
            ids = ", ".join(c["id"] for c in con["concepts"])
            sys.exit(f"Unknown concept {args.concept!r}.\nAvailable: {ids}")
        print(f"{m['label']}  [{m['id']}]\n")
        print(f"  Why it matters: {m['why']}\n")
        print(f"  Matched on: {', '.join(m['terms'])}")
        print(f"  Source: {m['source']}\n")
        by_id = {e["id"]: e for e in meta["files"]}
        print(f"  {m['matchingFiles']} files match; showing the strongest "
          f"{min(args.limit, m['shown'])}\n")
        for f in m["files"][: args.limit]:
            e = by_id.get(f["path"], {})
            print(f"  {f['hits']:5d} hits  {f['path']}  [{e.get('kind', '?')}]")
        return 0

    if args.file:
        e = next((x for x in meta["files"] if x["path"] == args.file), None)
        if not e:
            sys.exit(f"{args.file} is not in the index. "
                     f"Is it tracked? Is the index stale (`build.py --check`)?")
        print(json.dumps(e, indent=2))
        return 0

    q = " ".join(args.query).strip()
    if not q:
        c = meta["counts"]
        print(f"Index: {c['files']} files, {c['bytes'] / 1e6:.1f} MB, "
              f"{c['withSummary']} with a summary (commit {meta.get('commit')})")
        print(f"  by kind: {c['byKind']}")
        print("\nGive a query, or try --concepts. See --help.")
        return 0

    if args.semantic:
        hits = semantic(q)
        if hits is None:
            sys.exit("Semantic index unavailable. It is gitignored by design — "
                     "build it with:\n  python3 index/build.py semantic")
        show(hits, meta, args.limit, f"semantic: {q!r}", args.kind)
        return 0

    text = load(TEXT_JSON, "the text index")
    tx = bm25(q, text)
    if args.text:
        show(tx, meta, args.limit, f"text/BM25: {q!r}", args.kind)
        return 0

    sm = semantic(q)
    if sm is None:
        print("  (no semantic index — text only. Build: python3 index/build.py semantic)\n")
        show(tx, meta, args.limit, f"text/BM25: {q!r}", args.kind)
        return 0
    show(fuse(tx, sm), meta, args.limit, f"hybrid (BM25 + semantic): {q!r}", args.kind)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

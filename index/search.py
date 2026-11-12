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

**Semantic and hybrid make sure ollama is up.** Before embedding the query, a local ollama
is reached (started if it is not running) and the model checked; if that fails the search
says why and falls back to keyword. **Every query also runs the idle check**
(`idle.py`): if the semantic index is missing or stale and the machine is idle, a
low-priority background rebuild starts by itself and writes only gitignored files.

**Library use.** `run_query()` returns structured hits and never prints; the soltui Docs tab
uses it. The big structures (the 12 MB keyword postings, the embedding matrix) are read on
first use and held in `_CACHE`; `unload()` drops them.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "index"
if str(OUT) not in sys.path:  # sibling modules, whether run as a script or imported
    sys.path.insert(0, str(OUT))

import build  # noqa: E402
import idle  # noqa: E402
import ollama_ensure  # noqa: E402
INDEX_JSON = OUT / "INDEX.json"
TEXT_JSON = OUT / "TEXT-INDEX.json"
CONCEPT_JSON = OUT / "CONCEPT-INDEX.json"
SEMANTIC_NPZ = OUT / "semantic-embeddings.npz"
SEMANTIC_MANIFEST = OUT / "SEMANTIC-MANIFEST.json"
LOCAL_NPZ = OUT / "semantic-local.npz"
LOCAL_MANIFEST = OUT / "semantic-local.json"
# How long ollama keeps the embedding model resident after a query. The model is ~670 MB, so
# this is deliberately short: a burst of searches reuses it, an idle console does not hold it.
QUERY_KEEP_ALIVE = "2m"

# Loaded on first use, never at import. Keyed by file; cleared by unload().
_CACHE: dict[str, object] = {}

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


def _say(notes: list[str] | None, message: str) -> None:
    """Print for the CLI; collect for library callers (which must not write to stdout)."""
    if notes is None:
        print(f"  ({message})")
    else:
        notes.append(message)


def semantic_pair() -> tuple[Path, Path] | None:
    """(manifest, array) to search: the idle job's local pair if present, else the committed one."""
    for manifest, npz in ((LOCAL_MANIFEST, LOCAL_NPZ), (SEMANTIC_MANIFEST, SEMANTIC_NPZ)):
        if manifest.exists() and npz.exists():
            return manifest, npz
    return None


def _semantic_matrix(pair: tuple[Path, Path]):
    """(manifest, embeddings float32, owners), read once and cached by file and mtime."""
    import numpy as np

    with build.semantic_lock(pair[1]):
        stats = [p.stat() for p in pair]
        key = "semantic:" + str(pair) + repr([(s.st_ino, s.st_mtime_ns, s.st_ctime_ns, s.st_size) for s in stats])
        hit = _CACHE.get(key)
        if hit is not None:
            return hit
        manifest = json.loads(pair[0].read_text())
        if not isinstance(manifest, dict):
            raise ValueError("semantic manifest must be an object")
        data = pair[1].read_bytes()
        if manifest.get("arraySha256") and hashlib.sha256(data).hexdigest() != manifest["arraySha256"]:
            raise ValueError("semantic array and manifest do not belong to the same publication")
        with np.load(io.BytesIO(data), allow_pickle=False) as z:
            emb = z["embeddings"].astype("float32")
        owners = manifest.get("chunkOwners")
        if (emb.ndim != 2 or not np.isfinite(emb).all() or not isinstance(owners, list)
                or len(owners) != emb.shape[0] or any(not isinstance(owner, str) for owner in owners)
                or manifest.get("dims", emb.shape[1]) != emb.shape[1]):
            raise ValueError("semantic array shape or owner mapping is invalid")
        for stale in [k for k in _CACHE if k.startswith("semantic:")]:
            del _CACHE[stale]
        _CACHE[key] = (manifest, emb, owners)
        return _CACHE[key]


def semantic(query: str, limit: int = 40, notes: list[str] | None = None,
             *, start_ollama: bool = True) -> list[tuple[str, float]] | None:
    """Cosine similarity over chunk embeddings, best chunk per file.

    Returns None (rather than raising) when the array is absent or ollama cannot be
    reached, so hybrid can degrade to text and say so. Per-file score is the max over its
    chunks: a long document that answers the query in one paragraph should rank on that
    paragraph, not be diluted by the rest of itself.
    """
    pair = semantic_pair()
    if pair is None:
        return None
    try:
        import numpy as np
        import urllib.request
    except ImportError:
        return None
    try:
        man, emb, owners = _semantic_matrix(pair)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        _say(notes, f"semantic unavailable: invalid index evidence ({type(exc).__name__})")
        return None
    model = man.get("model", ollama_ensure.EMBED_MODEL)
    url = man.get("endpoint", f"{ollama_ensure.OLLAMA_BASE}/api/embed")
    status = ollama_ensure.ensure(model, ollama_ensure.base_of(url), start=start_ollama)
    if status.started:
        _say(notes, "ollama was not running; started it")
    if not status.ok:
        _say(notes, f"semantic unavailable: {status.message}")
        return None
    try:
        body = json.dumps({"model": model, "input": [query],
                           "keep_alive": QUERY_KEEP_ALIVE}).encode()
        req = urllib.request.Request(url, data=body,
                                    headers={"Content-Type": "application/json"})
        with ollama_ensure.local_urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
        vectors = d.get("embeddings") if isinstance(d, dict) else None
        if vectors is None and isinstance(d, dict) and "embedding" in d:
            vectors = [d["embedding"]]
        if not isinstance(vectors, list) or len(vectors) != 1:
            raise ValueError("query embedding response count is invalid")
        q = np.asarray(vectors[0], dtype="float32")
        if q.ndim != 1 or q.shape[0] != emb.shape[1] or not np.isfinite(q).all() or np.linalg.norm(q) == 0:
            raise ValueError("query embedding shape or values are invalid")
    except Exception as exc:  # noqa: BLE001 - any transport failure degrades to text
        _say(notes, f"semantic unavailable: {type(exc).__name__}")
        return None
    q /= (np.linalg.norm(q) or 1.0)

    if not owners:
        _say(notes, "semantic manifest has no chunkOwners; rebuild: python3 index/build.py semantic")
        return None
    if len(owners) != emb.shape[0]:
        _say(notes, f"semantic index is stale: {emb.shape[0]} vectors vs {len(owners)} owners; "
                    "rebuild: python3 index/build.py semantic")
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


@dataclass
class Hit:
    path: str
    score: float
    kind: str
    lines: int
    summary: str


@dataclass
class QueryResult:
    """What a library caller gets: ranked hits, the mode that actually ran, and why."""

    hits: list[Hit] = field(default_factory=list)
    mode_used: str = "keyword"
    notes: list[str] = field(default_factory=list)


MODES = ("keyword", "semantic", "hybrid")


def unload(model: bool = True) -> str:
    """Drop the cached postings and embedding matrix, and tell ollama to release the model.

    The embedding model is ~670 MB and ollama otherwise keeps it for `QUERY_KEEP_ALIVE`
    after the last query. `keep_alive: 0` asks for an immediate unload. This never starts a
    server: if ollama is not running there is nothing to release.
    """
    _CACHE.clear()
    if not model:
        return "cleared the in-process index cache"
    import urllib.request

    base = ollama_ensure.OLLAMA_BASE
    if not ollama_ensure.reachable(base, timeout=1.0):
        return "cleared the in-process index cache; ollama is not running"
    try:
        body = json.dumps({"model": ollama_ensure.EMBED_MODEL, "input": [""],
                           "keep_alive": 0}).encode()
        req = urllib.request.Request(f"{base}/api/embed", data=body,
                                     headers={"Content-Type": "application/json"})
        ollama_ensure.local_urlopen(req, timeout=10).read()  # noqa: S310 - local only
    except Exception as exc:  # noqa: BLE001 - best effort; the cache is already cleared
        return f"cleared the in-process index cache; could not unload the model ({type(exc).__name__})"
    return "cleared the in-process index cache and asked ollama to unload the embedding model"


def _cached_json(path: Path, what: str) -> dict:
    key = f"json:{path}:{path.stat().st_mtime_ns if path.exists() else 0}"
    hit = _CACHE.get(key)
    if hit is None:
        for stale in [k for k in _CACHE if k.startswith(f"json:{path}:")]:
            del _CACHE[stale]
        hit = _CACHE[key] = load(path, what)
    return hit  # type: ignore[return-value]


def run_query(query: str, mode: str = "hybrid", limit: int = 20, kind: str | None = None,
              *, start_ollama: bool = True, auto_index: bool = True) -> QueryResult:
    """Search without printing. `mode` is keyword, semantic or hybrid.

    Nothing is read until this is called, so importing the module costs nothing. Keyword
    never touches ollama. Semantic and hybrid make sure it is up (see `semantic`) and fall
    back to keyword with a note when it cannot be. `auto_index` runs the idle check.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    result = QueryResult()
    meta = _cached_json(INDEX_JSON, "the file metadata index")
    if auto_index:
        result.notes.append(idle.maybe_start(**({} if start_ollama else {"start_ollama": False})))
    tx: list[tuple[str, float]] = []
    if mode in ("keyword", "hybrid"):
        tx = bm25(query, _cached_json(TEXT_JSON, "the text index"))
    sm = None
    if mode in ("semantic", "hybrid"):
        sm = semantic(query, notes=result.notes, start_ollama=start_ollama)
        if sm is None:
            result.notes.append("no semantic result; "
                                + ("showing keyword results" if mode == "hybrid"
                                   else "nothing to show for semantic-only"))
    if mode == "keyword" or (mode == "hybrid" and sm is None):
        ranked, result.mode_used = tx, "keyword"
    elif mode == "semantic":
        ranked, result.mode_used = sm or [], "semantic"
    else:
        ranked, result.mode_used = fuse(tx, sm or []), "hybrid"
    by_id = {e["id"]: e for e in meta["files"]}
    for fid, score in ranked:
        e = by_id.get(fid)
        if not e or (kind and e.get("kind") != kind):
            continue
        result.hits.append(Hit(e["path"], float(score), e["kind"], int(e["lines"]),
                               e.get("summary") or ""))
        if len(result.hits) >= limit:
            break
    return result


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
    if q:
        print(f"  [{idle.maybe_start()}]")
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

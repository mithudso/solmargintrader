# The repository index

A searchable index over every tracked file in this repo: what exists, which files
contain a word, which files mean something like a question, and which bear on an
idea. Built to answer "where is the thing that does X" without reading every file.

```bash
python3 index/build.py all                       # metadata + text + concepts (offline)
python3 index/build.py semantic                  # embeddings (needs local ollama)
python3 index/build.py --check                   # exit 1 if stale — run this first

python3 index/search.py "how are costs applied"  # hybrid: BM25 + semantic
python3 index/search.py --text "fee_bps"         # exact terms
python3 index/search.py --semantic "why did this stop working"
python3 index/search.py --concepts               # list concepts
python3 index/search.py --concept evidence-floor
python3 index/search.py --file backtester/core/cpcv.py
python3 index/search.py --kind code-python "grid"

python3 index/make_files_doc.py                  # -> docs/FILES.md
python3 index/make_concepts_doc.py               # -> docs/CONCEPTS.md
```

## Relationship to `docs/high_signal_file_index.json`

There are two indexes in this repo and they do different jobs, so check you want
this one:

| | `docs/high_signal_file_index.json` | `index/` (here) |
|---|---|---|
| Coverage | **104** curated high-signal files | **every** tracked file |
| Purpose | a short list for an LLM to read first | lookup and search |
| Retrieval | none — it is a list | BM25, embeddings, concepts |
| Drift check | `scripts/check_docs.py` prunes dead paths | `build.py --check` re-hashes |

Use theirs to decide *what to read*; use this one to *find* something. Neither
subsumes the other, and both are checked in CI.

## The four indexes

| Artifact | Answers | Committed | Built by |
|---|---|---|---|
| `INDEX.json` | what files exist, and what each one is | yes | `build.py meta` |
| `TEXT-INDEX.json` | which files contain this word | yes | `build.py text` |
| `CONCEPT-INDEX.json` | which files bear on this idea | yes | `build.py concepts` |
| `semantic-embeddings.npz` | which files *mean* something like this | **no** | `build.py semantic` |
| `SEMANTIC-MANIFEST.json` | what the embedding index was | yes | `build.py semantic` |

## Three retrieval modes, because they fail differently

- **text** (BM25) is exact and explainable. It finds `fee_bps`; it cannot find
  "how much does trading cost".
- **semantic** (cosine over chunk embeddings) finds paraphrase. It answers "why did
  a backtest look good but fail later" with no shared keywords — and it cannot be
  trusted on an identifier, because it will happily rank `slippage_bps` beside
  `fee_bps` when you wanted one specifically. Note it also lags: the array covers
  whatever the corpus was at its last build, and `SEMANTIC-MANIFEST.json` records
  the per-file hashes so you can tell. Rebuild after the tree moves.
- **hybrid** (the default) fuses the two by rank, not score. A BM25 score and a
  cosine similarity are on different scales, so averaging them would let whichever
  is numerically larger win; reciprocal rank fusion only uses position.

## Four decisions worth knowing

**The embeddings are gitignored.** A few thousand chunks at 1024 float16 comes to
**more megabytes than the entire tracked source tree**, and it re-diffs on every
content change. `data/` is gitignored for the same reason. `SEMANTIC-MANIFEST.json`
is committed instead — model, dimensions, chunk count, chunk-to-file mapping,
per-file source hashes — so a reader can tell what the index *was* and whether it
would still be valid. `search.py --semantic` refuses with the rebuild command when
the array is absent.

Exact counts live in the manifest, not in this file, and deliberately so: every
figure here that was hardcoded went stale within the day, because the repo grew from
237 tracked files to 276 while the index was being built.

```bash
python3 -c "import json; m = json.load(open('index/SEMANTIC-MANIFEST.json')); \
print(m['chunks'], 'chunks over', m['files'], 'files,', m['dims'], 'dims,', m['model'])"
```

**No pickle.** The `.npz` holds only floats and the chunk-to-file mapping lives in
the JSON manifest, so loading never needs `allow_pickle=True`. Unpickling an array
is arbitrary code execution, which is not a risk an index a reader may regenerate
should carry.

**`--check` exists because staleness is the real failure mode.** An index looks
authoritative and goes stale silently on every commit. This repo has twice shipped
a result file nobody could re-derive, and one of them was wrong in a way that
survived precisely because nothing re-hashed it. `--check` re-hashes the tree and
exits non-zero listing what was added, removed or changed.

Two things are excluded from that hash, both deliberately: the index's own output
(including it made `--check` unsatisfiable — every build rewrote a file it had just
hashed) and `docs/FILES.md` / `docs/CONCEPTS.md`, which are generated *from* the
index and so cannot be inputs to it. "Stale" has to mean the source moved.

**The engine cannot reach this code.** `AGENTS.md` requires that the backtest
engine never touches the network, and `build.py semantic` opens a socket to
localhost ollama. Those coexist safely only while nothing under `backtester/` can
import `index/`, so `backtester/tests/test_index.py` asserts the absence of that
import edge in both directions, and asserts that only the embedding path can open a
socket at all. `build.py all` is offline.

## Concepts are the repo's own vocabulary

Not an invented taxonomy. They come from the `FAMILY` dict in
`backtester/core/strategies/__init__.py`, the strategy-card frontmatter,
`docs/trading-signals-concept-family.md`, and terms verified to recur in the
corpus. A concept matching no file is dropped by the builder rather than kept for
symmetry, and the dropped count is reported so the omission is visible.

The point is to find an idea under all the names it goes by. The evidence floor
appears as `min_total_trades`, `insufficient`, `DROPPED` and `rankable` in
different files, and no single keyword finds all four.

## Regeneration order

`docs/FILES.md` and `docs/CONCEPTS.md` are generated from the index, and they are
themselves tracked files, so build in this order:

```bash
python3 index/build.py all         # 1. index the source
python3 index/make_files_doc.py    # 2. write the derived docs
python3 index/make_concepts_doc.py
python3 index/build.py all         # 3. re-index so the docs' own hashes are current
python3 index/build.py --check     # 4. confirm the fixpoint
```

Step 3 matters: without it the index records the previous revision of the two docs.

## Where descriptions come from

`docs/FILES.md` marks every entry, because a generated one-liner and a considered
one should not look alike:

- **curated** — hand-written purpose and usage, held as data in the `CURATED` table
  of `make_files_doc.py` so a rebuild never discards it. Used for the engine, the
  research drivers, the order-placing path, and every file with no prose of its own.
- **extracted** — the file's own module docstring, JSDoc header, or frontmatter
  `summary`. Trustworthy here because nearly every Python module and JS file carries
  a substantial one — `docs/FILES.md` prints the exact ratio, computed at generation
  time rather than hardcoded, because a frozen figure here was wrong within a day.
- **derived** — shape only, for generated artifacts: a CSV's header and row count,
  a JSON's keys. Prose for a result file would be invented.

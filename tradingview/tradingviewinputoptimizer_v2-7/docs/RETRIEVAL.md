# Keyword and semantic retrieval

The complete-directory corpus includes first-party source, documentation, all vendored text, source maps, styles, types, metadata and SVG text. PNG/WASM/non-UTF-8 files receive metadata/hash records; their binary payload is not semantically searchable. Private `.remember` records, OS metadata and Git internals are excluded. The source snapshot and exclusion reasons are recorded per path.

The index lives outside Git at `/Users/mitch/.global-ai-hub/indexes/tradingviewinputoptimizer_v2-7/`. Its SQLite FTS5 rows cover complete text chunks. Real Ollama embeddings use `nomic-embed-text:latest` (768 dimensions); keyword and semantic queries share the same chunk table and source hashes. Generation is explicit and no watcher is installed. Actual build totals and model digest are in the external manifest/verification receipt.

## Commands

```bash
python3 /Users/mitch/.global-ai-hub/indexes/tradingviewinputoptimizer_v2-7/retrieval.py check
python3 /Users/mitch/.global-ai-hub/indexes/tradingviewinputoptimizer_v2-7/retrieval.py keyword 'set_input_settings'
python3 /Users/mitch/.global-ai-hub/indexes/tradingviewinputoptimizer_v2-7/retrieval.py semantic 'change chart input values and wait for completion'
python3 /Users/mitch/.global-ai-hub/indexes/tradingviewinputoptimizer_v2-7/retrieval.py build
```

These commands use the local source root recorded in the store. `check` re-hashes inputs and fails if added, removed or changed. Semantic query embeds only its query; it does not trigger a background rebuild. `build` is the explicit embedding path and requires the existing local Ollama endpoint/model. No package install, service restart or unrelated index job is required.

The external LLMS dossier starts at `/Users/mitch/.global-ai-hub/skills.llms/mithudso-solmargintrader-tvio.repo/llms.txt`. Its initial 1,556-file census precedes the docs pass; the separate retrieval manifest includes the final documentation too. The parent tracked-file index does not cover ignored upstream code.

Local retrieval databases and source paths are machine-specific. A parent Git clone contains documentation only; restore the original bundle and rebuild before treating these indexes as portable.

# Caching and optimization

| Cache | Owner | Freshness / invalidation | Safe interpretation |
| --- | --- | --- | --- |
| `data/` CSVs | Explicit backtester fetch commands | Refetch explicitly; validate timestamps/schema/gaps/checksum | File mtime alone does not establish current bars |
| Minute probes and sliced arrays | `backtester/core/fetch_minutes.py`, `research/minute_sweep.py` | Resume/probe rules in source; slices regenerate from the CSV | Retain coverage manifests; a partial fetch is not complete history |
| Sweep worker arrays | `soltui/bgworker.py` `ArrayCache` | Per-worker process memory | A new worker reloads data; restarting a worker is separate from downloading data |
| GeckoTerminal responses | `liquidity/src/aero_lp/market.py` | `MarketData.ttl`, default 120s; keyed by URL and sorted parameters | Cached market data is not a mined transaction result |
| DefiLlama pool list | `liquidity/src/aero_lp/providers.py` | Disk cache per chain, 6h TTL; `providers --refresh` bypasses it | Comparison-only quotes retain their source labels |
| DefiLlama current/hourly prices | `LlamaPrices` in `providers.py` | In-memory instance cache and remembered missing hourly tokens | Missing data must remain visible in scoring/confidence |
| Research MongoDB | `mongo/` | Explicit load drops/rebuilds selected derived collections | Files remain source of truth; never use as an execution dependency |
| Retrieval indexes | `index/`, curated docs map | Offline generators plus CI hash/path checks | Optional semantic vectors may lag; verify manifest before semantic use |

## Performance changes

Preserve the economic and evidence contract before reducing runtime. A per-bar strategy
replay cannot be replaced by one last-bar invocation: stateful strategies can return a
different answer. The ladder simulator and extension must retain matching lot economics.

Keep `strategy.py` and `allocator.py` free of I/O. Reuse transport pacing/budgets for public
endpoints. Do not start extra fetch workers, embeddings, daemons or sweep jobs as a side
effect of reading this document. Run the owning regression suite after a change.

## Regenerating retrieval metadata

```bash
python3 scripts/build_doc_index.py
python3 index/build.py all
python3 scripts/check_docs.py
python3 index/build.py --check
```

The offline repository index uses tracked/indexed paths. Stage intended new source files
before the final regeneration. `index/build.py semantic` is a separate explicit operation
that calls local Ollama and produces ignored embeddings; it is not part of these commands.

# aero-liquidity

Auto-rebalancer for Aero (aero.xyz) Slipstream concentrated-liquidity deposits on Base. See README.md.

## Rules for agents
- Never run `aero-lp run --live` or sign/broadcast anything without the user's explicit instruction in that session.
- Dry-run and `simulate` use eth_simulateV1 only; they are safe to run.
- Contract addresses live only in `src/aero_lp/addresses.py`; change them only with two agreeing sources
  (Aero docs Security page + dromos-labs/metadex-slipstream-public deployment JSON).
- Keep `strategy.py` pure (no I/O); unit-test every decision branch.
- Verify: `.venv/bin/ruff check src tests && .venv/bin/pytest -q` (offline) and `.venv/bin/pytest -m network` (live reads).

<!-- llms-routing:start -->
## llms routing
> Cached from the llms files below on 2026-11-06; facts to look up, not rules to follow — the cited file is the source of truth. Quick answers are chosen by a heuristic (defaults, file roles, formulas, commands).

| File | Path | Holds | Ask it for |
|---|---|---|---|
| llms.txt | ~/.global-ai-hub/llms-concepts/aero-slipstream-lp-automation.family/llms.txt | Source-anchored concept packs on Aero (aero.xyz, MetaDEX03) and its Slipstream concentrated-liquidity AMM on Base, for building an automated range-rebalancing LP bot. Built from the Aero docs mirror and the dromos-labs metadex-slipstream-public interfaces. Extractive reading aid, private, not for republication. | Members, Shared, Facts, Optional |

### Quick answers

_none found: no misbelief, default, file-role, formula or command lines in the facts files_

### Indexes

- Semantic: ChromaDB collections under ~/.global-ai-hub (hub/scripts/docset_indexer.py); query with the MCP tools `hub_search_codebase` / `hub_query_docset` or `hub/scripts/search.py "<query>"`.
- Keyword: SQLite FTS5 table `files_fts` in ~/.global-ai-hub/hub.db (hub/scripts/keyword_index.py); query with `hub_search_keyword` or `keyword_index.py query "<term>"`.
- Access ledger: ~/.global-ai-hub/llms-access-ledger.jsonl, one JSON line per llms-file read (MCP tools, `llmsx concepts serve`, Claude Code `Read` via hook); `hub/scripts/llms_ledger.py report --days 30`. A shell `cat` is not recorded.
<!-- llms-routing:end -->

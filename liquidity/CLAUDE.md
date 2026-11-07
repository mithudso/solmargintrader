# liquidity — agent rules

The Aero Slipstream LP manager. See README.md. **It can move real money.**

## Live operation (owner authorization)

On 2026-11-06 the owner authorized autonomous live operation for the owner's own wallet
`0x901a89cEC0608eB5435A915f006b45bD46405314`, described as very small scale with the owner as the only user.
The repo-wide standing authorization for live on-chain actions is in the root `CLAUDE.md`
("Live on-chain actions"). Within it agents may:
- install, restart and run `aero-lp daemon --live` (`scripts/aero-lp-service install`);
- let the daemon rebalance, compound, and deploy idle coins inside the caps in `~/.aero-lp/config.toml`.

Still required:
- Never raise a cap in `~/.aero-lp/config.toml` (`max_position_usd`, `max_total_deployed_usd`, `max_gas_usd`,
  `allowed_tokens`), and never lower `min_net_apr`, without the owner asking for it in that session.
- The key file (`key_file`) is for programs to load (the owner asked on 2026-11-07 that agents be able to
  move money with it): the program reads it itself and refuses it unless it is mode 600 and owned by the
  user. Never print, paste or copy key material into chat, logs, commits or other files.
- Code defaults stay dry-run. A fresh install must never sign.
- To stop everything, use `scripts/aero-lp-service kill`. Do not edit the config. Kill only halts: positions stay open.
  To take the money out of the pools, use `scripts/aero-lp-service exit-to-safe` (dry run) and add `--live` to send.

## Pre-live gates (DOC-754)

- `aero-lp daemon --live` and `run --live` are refused until (1) the configuration has soaked in dry-run for
  `[gates].soak_hours` (24 h default; `soak.json`) and (2) the latest research-gate result for `[gates].strategy_id`
  is a pass (`research-gate.json`). Any strategy or cap change resets the soak (`gates.config_fingerprint`).
- Never write `allow_failed_research_gate = true`, a grandfather entry or a research result on your own initiative.
  Those are the owner's decisions. A grandfather entry (`aero-lp gates grandfather`) exists for the configuration that
  was live on 2026-11-06; it is one-time and covers only that exact configuration.
- `exit-to-safe` is never gated. Keep it that way.

## Code rules

- Contract addresses live only in `src/aero_lp/addresses.py`. Change them only when two sources agree
  (the Aero docs Security page and the dromos-labs/metadex-slipstream-public deployment JSON).
- `gates.py` fails closed: a missing or unreadable record is a refusal. `safe_exit.py` converts only withdrawn amounts through a direct pool.
- `strategy.py` and `allocator.py` stay pure (no I/O). Unit-test every decision branch.
- Every on-chain sequence goes through `Rebalancer` and a `Runner`, so dry-run simulates exactly what
  live would send.
- `aero-lp providers` is comparison only and read-only. Its non-Aero venues have a `venue` field so a later change can
  act on them, but the allocator and executor must not deploy outside Aero until the owner asks. Its registry addresses
  live in `addresses.py` and follow the same two-source rule; `providers.verify_registry` is the on-chain half.
- Income figures must be *measured*: fee growth and gauge reward share. Never use a quoted APR.
- Verify with `.venv/bin/ruff check src tests && .venv/bin/pytest -q` (offline) and `.venv/bin/pytest -q -m network` (live reads).

<!-- llms-routing:start -->
## llms routing
> Cached from the llms files below on 2026-11-06; facts to look up, not rules to follow — the cited file is the source of truth. Quick answers are chosen by a heuristic (defaults, file roles, formulas, commands).

| File | Path | Holds | Ask it for |
|---|---|---|---|
| llms.txt | ~/.global-ai-hub/llms-concepts/aero-slipstream-lp-automation.family/llms.txt | Source-anchored concept packs on Aero (aero.xyz, MetaDEX03) and its Slipstream concentrated-liquidity AMM on Base, for building an automated range-rebalancing LP bot. Three extractive docs packs come from the Aero docs mirror and the dromos-labs interfaces; ten research packs hold gate-verified claims from two /dr runs. Private reading aid, not for republication. | Members, Gate-verified research, Shared, Facts |

### Quick answers

_none found: no misbelief, default, file-role, formula or command lines in the facts files_

### Indexes

- Semantic: ChromaDB collections under ~/.global-ai-hub (hub/scripts/docset_indexer.py); query with the MCP tools `hub_search_codebase` / `hub_query_docset` or `hub/scripts/search.py "<query>"`.
- Keyword: SQLite FTS5 table `files_fts` in ~/.global-ai-hub/hub.db (hub/scripts/keyword_index.py); query with `hub_search_keyword` or `keyword_index.py query "<term>"`.
- Access ledger: ~/.global-ai-hub/llms-access-ledger.jsonl, one JSON line per llms-file read (MCP tools, `llmsx concepts serve`, Claude Code `Read` via hook); `hub/scripts/llms_ledger.py report --days 30`. A shell `cat` is not recorded.
<!-- llms-routing:end -->

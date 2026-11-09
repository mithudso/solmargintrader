# Retrieval before exploration

Use the configured global AI hub semantic search first when it is available. If the
connector is unreachable or returns no relevant hit, use the existing local keyword
index (`python3 index/search.py --text "<query>"`) and targeted source reads. See
`index/README.md`. Do not start an indexer, watcher, inference runtime or embeddings
merely to begin a repository task. Semantic regeneration is a separate explicit action.

# CLAUDE.md — solmargintrader

Instructions for agents working in this repository. Read before changing code.

## Workflow records

Save each user request verbatim in `prompts.md` before implementation. Keep `memory.md`
current with the target, completed work, verification, and remaining steps. Increment the
record version and its delta fields on each update. These workflow versions are separate
from component package versions. Commit only the files owned by the current task.

## What this is

Seven components with different risk profiles. Know which one you are in:

| Component | Risk |
| --- | --- |
| `backtester/` (Python) | Simulation only. **Never add live-trading capability here** — see its README's Scope section. The danger is a dishonest backtest, not a lost trade. |
| `research/` (Python) | Analysis built on the backtester. The danger is overstating a result. |
| `extension/` (JavaScript) | **Can place real orders and move real money.** Treat every change as production software. |
| `soltui/` (Python) | macOS research console with a separately armed manual Coinbase spot-order path and optional no-confirmation mode. |
| `mongo/` (Python) | Derived local datastore. Rebuildable from the repo; nothing else imports it. |
| `executor/` (Python) | **Moves real money** on Solana: guarded spot swaps through Jupiter. It signs and sends. Its own venv and pytest. Read `executor/CLAUDE.md` first: rails, verifier, journal, and what is not built yet. |
| `liquidity/` (Python) | **Moves real money** on Aero (Base). It manages, compounds and allocates LP positions. Its own venv and pytest. Read `liquidity/CLAUDE.md` first: it records the owner's live-operation authorization and its limits. |

## Live on-chain actions (owner's standing authorization)

**Liquidity archive, 2026-11-08:** The owner discontinued the liquidity manager and scout as unprofitable. Keep the Aero LP service disabled and the kill switch set unless the owner later requests reactivation. See `liquidity/CLAUDE.md`.

The owner has given this instruction three times (last on 2026-11-06). Do not ask for it again.

For the owner's own wallets, agents may act live without a further confirmation:
- Base `0x901a89cEC0608eB5435A915f006b45bD46405314` (key file `~/.ssh/wallet.private`);
- Solana `EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV` (key file `~/.ssh/solana.private`).

To read the Base wallet (balances, the tokens the owner really uses, history), use the CDP MCP exactly as
`docs/BASE-WALLET-QUERIES.md` says: paginated token balances, time-bounded SQL, spam filtered by the owner's
own transactions.

Agents may:
- send live blockchain requests (reads, simulations and transactions) when the result gives useful information;
- buy, sell, swap, deposit and withdraw tokens when there is a clear and provable reason.

Conditions:
1. Validate the hypothesis first, as far as possible: model, backtest, quote, and simulate the exact
   transaction (`eth_simulateV1` on Base, `simulateTransaction` on Solana). Real money tests what survived that.
2. Record the reason and the evidence before sending, and report every transaction hash to the owner.
3. Keep each test as small as the test allows.
4. Agents have the key files: run the programs that load them to sign and move money (the owner asked for
   this explicitly on 2026-11-07; `liquidity`'s `load_signer` checks owner, mode 600 and the address). Never
   print, paste or copy key material into chat, logs, commits or other files, and keep both files mode 600.
5. The liquidity daemon still obeys its kill switch and the caps in `~/.aero-lp/config.toml`. Never raise a
   cap or lower `min_net_apr` without the owner asking (`liquidity/CLAUDE.md`).
6. Never visit or call the contracts or sites of unsolicited airdrop tokens. Burning them and closing their
   accounts through the standard token program is allowed.

Component boundaries still hold: `backtester/` stays simulation-only, and code defaults stay dry-run.
The executor's own rails (`executor/CLAUDE.md`) are the live path for swaps: use `executor swap` rather than ad hoc scripts.

## Non-negotiables — extension

1. **Dry-run stays the default.** `DEFAULT_CONFIG.mode` is `dry-run` and the extension installs
   disarmed. Never change a default so a fresh install can place an order.
2. **Risk rails live in code.** Every rail is a gate in `src/core/risk.js` that an order must pass. A
   rail documented but not enforced is not a rail. Rails must **fail closed** — a missing or NaN
   state field must not silently disable one (see `normaliseState`).
3. **Never guess a number that becomes an order.** If a price, quantity or fee is missing or
   unusable, refuse and surface it. Do not fall back to config, and do not fall back to zero.
4. **Reconcile before plan.** The venue's live order list is the source of truth at the top of every
   tick; local state is a cache. An intent that was submitted but is not live becomes `unknown` and
   is **never auto-retried** — that is how a rung double-fires after a crash.
5. **No secret material in logs, `chrome.storage.sync`, the DOM, or a response body.** The API key
   and the session-key vault are `chrome.storage.local` / mode-0600 file only. `setApiKey` returns a
   length, never the key.
6. **Three surfaces, one registry.** Every action belongs in `src/core/commands.js`. Do not add a
   message handler, CLI branch or HTTP route carrying its own logic — `test/surfaces.test.js` will
   fail, and correctly so.
7. **The exit is one rung above the entry.** A sell placed at the level it was bought at captures
   zero and pays two fees. `expectedRoundTripUsd` and its test exist because this bug shipped once.
8. **Market reads stay reads, and swaps stay quotes.** `src/market/net.js` refuses any JSON-RPC
   method that is not a read; `src/market/quote.js` returns a quote and a hand-off URL, never a
   transaction. A quoted APY (DefiLlama) may raise only an "info" lead; only the Aero scout's modelled figures (fresh, backtest-positive,
   medium or high confidence, unflagged) may raise an "act" alert (`src/core/alerts.js`, Stele KNOW-837, KNOW-838).

## Non-negotiables — backtester

1. **Correctness of the simulation outranks the number of strategies.** A tool that honestly reports
   a losing strategy is a success; one that reports an inflated Sharpe from a leaked bar is a
   failure even if it runs.
2. **No lookahead.** A signal at bar *t* may only use data through bar *t*. Any change touching
   signal generation or fill timing needs a test that would catch a one-bar leak.
3. **Costs are never optional.** Fees, slippage and the perp borrow fee stay in the P&L path.
4. **The engine does not touch the network.** Fetching is a separate, explicit step
   (`backtester.core.fetch`) writing a local cache.
5. **Every registered strategy has a card.** `backtester/strategy_cards/<id>.md` carries its
   equations, reasoning, limitations and parameter defaults, and `tests/test_strategy_cards.py`
   checks the machine-readable half against the code in both directions — a registry entry with no
   card fails, and so does a card whose defaults have drifted. Add the card in the same commit as
   the strategy.
6. **The ladder grid must agree with the extension.** `core/gridsim.py` is a port of
   `extension/src/core/grid.js`; a change to either one's economics needs the matching change in the
   other, or the backtest becomes a confident wrong number about the live strategy. Do not confuse it
   with the `grid` strategy in `core/strategies/signals.py`, which is an exposure staircase, not a
   ladder of resting orders.

## Before you claim a change works

```bash
python3 -m unittest discover -s backtester/tests -t .   # 909 tests
python3 -m unittest discover -s soltui/tests -t .       # 1211 tests (~840s, optional)
python3 -m unittest discover -s mongo/tests -t .        # 34 tests
cd extension && npm test                                # 372 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100    # a round trip must still close positive
cd extension && npm run e2e                             # real Chrome for Testing: load, dry-run, rails (needs one; see below)
node tools/verify-endpoints.js                          # live Jupiter reachability
python3 scripts/check_docs.py                           # doc counts and retrieval indexes
cd liquidity && .venv/bin/pytest -q                     # liquidity (own venv; -m network for live reads)
cd executor && .venv/bin/pytest -q                      # executor (own venv; -m network for live read-only quotes and simulations)
```

`npm run e2e` (`extension/tools/e2e.mjs`) loads the unpacked extension into Chrome for Testing over the
DevTools pipe and checks loading and dry-run behaviour in a real browser (needs Chrome for Testing:
`npx @puppeteer/browsers install chrome@stable`, or set `CHROME`; exit 2 means no usable browser).
It never arms, signs or changes mode, limits or keys (`extension/e2e/lib/guard.mjs` enforces that),
and it blocks all network but a stubbed price read. It does not verify live orders. Do not describe
it as live verification; the headless dry run stays the economics gate.

## House style

**JavaScript** — ESM, no build step, **no npm runtime dependencies**. The one sanctioned runtime
library is TradingView Lightweight Charts 5.2.1, vendored and pinned in `extension/vendor/lightweight-charts/`
(owner's choice 2026-11-07; read its README before touching it). Do not add a package to solve
something the ~150 lines of `src/wallet/solana.js` already solve. Tests are `node:test` +
`node:assert/strict`. Keep `src/core/grid.js`, `risk.js` and `pnl.js` free of I/O and `chrome.*`.

**Python** — 3.13, stdlib-first. Backtester dependencies live in
`backtester/requirements.txt`; its tests use `unittest` and deliberately exclude
`pyarrow`, `requests`, and `pytest`. `mongo/` and `soltui/` declare their own requirements.
`liquidity/` and `executor/` use their own `pyproject.toml`, locked virtualenv, `pytest`, and Ruff; follow
`liquidity/CLAUDE.md` and `executor/CLAUDE.md` there. Use `from __future__ import annotations` and type hints.

**Both** — comments explain *why*, especially where the obvious implementation is wrong (MV3 timers,
base58 zero bytes, FIFO vs paired-lot attribution, one-bar leaks). Do not narrate *what*.

## Known-unverified areas

Read "Verification status" in `extension/README.md` before extending it. In short: **no live order
has ever been placed**. The unpacked extension is now loaded and exercised in a real browser (`npm run e2e`,
dry-run only), so the MV3 load path, service worker, popup, dashboard and message routing are
covered; live trading is not. Trigger history/cancellation have public-contract fixtures, but authenticated
wallet responses, execution USD valuation and fee attribution remain unverified. The bundled signer
has no semantic transaction verifier, so Trigger live signing stays blocked. `executor/src/executor/txverify.py` is a semantic verifier for Jupiter Swap v1 transactions (not for Trigger). Do not present live
execution as working.

SolTUI's manual Jupiter V2 path provides unsigned, structurally checked previews only. Submit and
quick-submit refuse before key loading, signing or sending until independent V2 economic verification
exists. Keep uncertain historical submissions blocking until chain evidence resolves them. A timeout
alone never proves absence. Manual Coinbase orders remain a separately armed path.

## Related

`AGENTS.md` points here. Component detail lives in `backtester/README.md` and
`extension/README.md`; cross-cutting detail in `docs/`.

<!-- llms-routing:start -->
## llms routing
> Cached from the llms files below on 2026-11-08; facts to look up, not rules to follow — the cited file is the source of truth. Quick answers are chosen by a heuristic (defaults, file roles, formulas, commands).

| File | Path | Holds | Ask it for |
|---|---|---|---|
| llms.txt | ~/.global-ai-hub/llms-concepts/five-minute-sol-perps-task808-suite.family/llms.txt | Seven private reference packs compile accepted authored claims about executable short-horizon SOL signals. They retain scoped evidence and open limitations; this suite does not demonstrate a live trading edge. | Products, Navigation |
| llms-sitemap.txt | ~/.global-ai-hub/llms-concepts/five-minute-sol-perps-task808-suite.family/llms-sitemap.txt | Kind: store · Entries: 7 · Internal private reading aids | Files, Resources |

### Quick answers

_none found: no misbelief, default, file-role, formula or command lines in the facts files_

### Indexes

- Semantic: ChromaDB collections under ~/.global-ai-hub (hub/scripts/docset_indexer.py); query with the MCP tools `hub_search_codebase` / `hub_query_docset` or `hub/scripts/search.py "<query>"`.
- Keyword: SQLite FTS5 table `files_fts` in ~/.global-ai-hub/hub.db (hub/scripts/keyword_index.py); query with `hub_search_keyword` or `keyword_index.py query "<term>"`.
- Access ledger: ~/.global-ai-hub/llms-access-ledger.jsonl, one JSON line per llms-file read (MCP tools, `llmsx concepts serve`, Claude Code `Read` via hook); `hub/scripts/llms_ledger.py report --days 30`. A shell `cat` is not recorded.
<!-- llms-routing:end -->

### Existing Solana margin family

The earlier broad family remains available alongside the five-minute suite. Its source-check date and historical verification scope remain those stated in the retained row.

| File | Path | Holds | Ask it for |
|---|---|---|---|
| llms.txt | ~/.global-ai-hub/llms-concepts/solana-margin-trading-defi.family/llms.txt | Twelve concept packs for building Solana-first lending, looping, perp-short and fast-signal tooling with EVM comparisons. Every unit in the -v4 packs passed the research-gate/v4 evidence gate on 2026-11-06 (708 claims kept of about 5,000 researched; the rest could not be bound to exact source quotes or were not judged SUPPORTED). Educational, not financial advice; leverage can lose more than the stake; private reading aid. | Members, Shared, Facts, Optional |

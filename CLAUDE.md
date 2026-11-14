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

## Repository shape

See `docs/COMPONENTS.md` for APIs and `docs/codebase-overview.md` for source paths.
The existing maintained wiki is documented in `docs/ECOSYSTEM-WIKI.md`.

## What this is

Eleven components with different risk profiles. Know which one you are in:

| Component | Risk |
| --- | --- |
| `website/` (JavaScript/Python) | Public wallet-account and subscription workspace on Cloudflare; Stripe can charge members when configured. Trading definitions remain inactive paper configurations. The separate Python adapter only reads public-market analysis inputs. No owner keys or local control-room access. |
| `ecosystem/` (Python) | Paper-only setup, durable F5 coordination, external bot registrations, sanitized manager telemetry and a local paper control room with authenticated, durable owner actions. Reuses existing workers and recorder. Never arms or submits orders. |
| `oracle/` (Python) | Source-labelled shadow forecasts and a historical event archive with read-only MCP subscriptions. Forecasts never sign or submit orders; the optional explicitly enabled TradingView worker submits Coinbase spot orders or owner-configured Jupiter ZEC Beta perpetual orders through GUM. Reference agreement is not profit probability; unavailable inputs fail closed. See `docs/JUPITER-ZEC-WEBHOOK.md` for the separate leveraged signing and account boundary. |
| `botmanager/` (Python) | Standalone `solbot` lifecycle and evidence application. Default paper/disarmed. Legacy adapters preserve the existing owner; missing data, credentials or execution capability fail closed. Never silently seize a bot or create a duplicate recorder/optimizer. |
| `backtester/` (Python) | Simulation only. **Never add live-trading capability here** — see its README's Scope section. The danger is a dishonest backtest, not a lost trade. |
| `research/` (Python) | Analysis built on the backtester. The danger is overstating a result. |
| `extension/` (JavaScript) | **Can place real orders and move real money.** Treat every change as production software. |
| `soltui/` (Python) | macOS research console with a separately armed manual Coinbase spot-order path and optional no-confirmation mode. |
| `mongo/` (Python) | Derived local datastore. Rebuildable from the repo; nothing else imports it. |
| `executor/` (Python) | **Moves real money** on Solana: guarded spot swaps through Jupiter. It signs and sends. Its own venv and pytest. Read `executor/CLAUDE.md` first: rails, verifier, journal, and what is not built yet. |
| `liquidity/` (Python) | **Moves real money** on Aero (Base). It manages, compounds and allocates LP positions. Its own venv and pytest. Read `liquidity/CLAUDE.md` first: it records the owner's live-operation authorization and its limits. |

The separate `website/` package hosts the public wallet-account and research workspace
on Cloudflare. Its tenant-owned bot definitions stay inactive and paper-only. D1 account
storage, Stripe billing, the read-only Python analysis bridge and live execution have
separate readiness gates. The website never inherits the local owner's credentials or
trading authority. Read [website/README.md](website/README.md) before changes. Its Node
tests and syntax checks run with `npm test` and `npm run check` from `website/`; its
Python/export checks are listed in [docs/TESTING.md](docs/TESTING.md).

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

Oracle uses its own installed environment: `python -m pip install ./backtester ./oracle ./botmanager ./soltui`, then `python -m unittest discover -s oracle/tests -t . -v` and `ruff check oracle`. Live feed availability and executor enforcement are separate gates; no unit test proves them.

Ecosystem setup and control room use `python -m pip install ./backtester ./oracle ./botmanager ./soltui ./ecosystem`, then `python -m unittest discover -s ecosystem/tests -t . -v` and `ruff check ecosystem oracle scripts/bootstrap_ecosystem.py`. Verify the installed environment and actual loopback UI separately. See `docs/ECOSYSTEM-BOOTSTRAP.md`.

```bash
python3 -m unittest discover -s backtester/tests -t .   # 1196 tests
python3 -m unittest discover -s soltui/tests -t .       # 1694 tests (TUI dependencies required)
python3 -m unittest discover -s mongo/tests -t .        # 73 tests
cd extension && npm test                                # 555 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100    # a round trip must still close positive
cd extension && npm run e2e                             # real Chrome for Testing: load, dry-run, rails (needs one; see below)
node tools/verify-endpoints.js                          # live Jupiter reachability
python3 scripts/check_docs.py                           # doc counts and retrieval indexes
(cd liquidity && .venv/bin/pytest -q)                    # liquidity (own venv; -m network for live reads)
(cd executor && .venv/bin/pytest -q)                     # executor (own venv; -m network for live read-only quotes and simulations)
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

The maintained family below captures 2026-11-12 static navigation. Its file cards
are shallow; optimizer coverage, tests, installation and runtime acceptance retain
separate receipts and limits. Source and parser definitions remain authoritative.

| File | Repository path | Purpose |
| --- | --- | --- |
| Index | [llms.txt](llms.txt) | Choose a reference |
| Digest | [llms-small.txt](llms-small.txt) | Read before source changes |
| Facts | [llms-facts.txt](llms-facts.txt) | Source-tagged claims and corrections |
| Reference | [llms-full.txt](llms-full.txt) | Ownership and evidence limits |
| File cards | [llms-filemap.txt](llms-filemap.txt) | All captured paths; shallow cards |
| Executables | [llms-executable.txt](llms-executable.txt) | Static parser/config/env declarations and unknowns |
| Indexes | [llms-indexes.txt](llms-indexes.txt) | Store declarations; no probes |
| Infrastructure | [llms-infra.txt](llms-infra.txt) | CI, schedules, env names, unverified links |
| History | [llms-history.txt](llms-history.txt) | 200-commit metadata window |
| Sitemap | [llms-sitemap.txt](llms-sitemap.txt) | Compact path/role list |

Quick answers:

- Ten trading components plus the separate hosted website retain independent owners. [src: README.md; docs/COMPONENTS.md]
- Misbelief: SolTUI is read-only and cannot move money. Actually: it retains a separately armed manual Coinbase path. [src: docs/repo-bootstrap-audit-2026-11-11.md; CLAUDE.md#what-this-is]
- Misbelief: Jupiter has no public REST write API for leveraged orders. Actually: the separate GUM Beta API supports the optional Oracle ZEC order Action path; the extension Perps adapter remains read-only. [src: https://github.com/mithudso/solmargintrader/blob/5914d2268b770079e54078e4479d166e9c75c90e/llms-facts.txt; README.md#two-findings-that-shaped-the-extension; docs/JUPITER-ZEC-WEBHOOK.md]
- Misbelief: Every repository search dispatches the idle semantic-index check. Actually: current keyword run_query skips idle dispatch; semantic and hybrid modes retain the guarded check. [src: https://github.com/mithudso/solmargintrader/blob/5914d2268b770079e54078e4479d166e9c75c90e/index/README.md#ollama-idle-indexing-and-the-docs-tab; index/search.py:311]

Use the existing hub retrieval connector when available. For bounded local text
retrieval, set `INDEX_NO_AUTO=1` and use `index/search.py --text "<query>"`.
Semantic embeddings and inference remain separate explicit operations. See
[index guidance](index/README.md), [testing](docs/TESTING.md) and the
[bounded bootstrap report](docs/repo-bootstrap-audit-2026-11-12.md). Historical
outside-repository dossiers do not prove current source or installed state.
<!-- llms-routing:end -->

### Existing Solana margin family

The earlier broad family remains available alongside the five-minute suite. Its source-check date and historical verification scope remain those stated in the retained row.

| File | Path | Holds | Ask it for |
|---|---|---|---|
| llms.txt | ~/.global-ai-hub/llms-concepts/solana-margin-trading-defi.family/llms.txt | Twelve concept packs for building Solana-first lending, looping, perp-short and fast-signal tooling with EVM comparisons. Every unit in the -v4 packs passed the research-gate/v4 evidence gate on 2026-11-06 (708 claims kept of about 5,000 researched; the rest could not be bound to exact source quotes or were not judged SUPPORTED). Educational, not financial advice; leverage can lose more than the stake; private reading aid. | Members, Shared, Facts, Optional |

## Website verification and activation boundaries

The hosted application is separate from the local owner control room. Read
`website/README.md` and `website/engine/README.md` before editing its boundaries.
Wallet sign-in grants no trading permission. Only verified Stripe subscription
state grants membership; missing billing or analysis configuration fails closed.
Never reuse the owner’s wallet keys or exchange credentials for public accounts.

```bash
npm --prefix website test
npm --prefix website run check
python3 -m unittest website.engine.test_server website.engine.test_research
python3 -m website.scripts.export_research --check
```

The website CI job runs those source gates. Production acceptance also needs the
actual deployed wallet/session round trip and content identity. A configured
binding, a paid redirect, or a saved bot does not establish analysis availability
or trading execution. `website/scripts/smoke.mjs` performs an explicit account
creation/deletion test; it is not a read-only health probe.

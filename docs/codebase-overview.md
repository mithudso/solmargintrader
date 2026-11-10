# Codebase overview

A file map for orientation, grouped by directory. Every path here is checked by
`scripts/check_docs.py`, so a rename that is not reflected below fails the build.

Ten components with separate execution boundaries:

| Component | Language | Can it move money? |
| --- | --- | --- |
| `ecosystem/` | Python 3.13 | No — paper orchestration, owner controls and local control room |
| `oracle/` | Python 3.13 | No — source-labelled observations and shadow forecasts |
| `botmanager/` | Python 3.13 | No — manager 0.7, fenced paper workers and availability suite |
| `mongo/` | Python 3.13 + pymongo | No — a derived datastore, rebuildable |
| `research/` | Python 3.13 | No — analysis over the backtester |
| `soltui/` | Python 3.13 | **Yes** — manual Coinbase path is separately armed; research runtime remains paper-only |
| `backtester/` | Python 3.13 | No — simulation only, by design |
| `extension/` | JavaScript (ESM, no deps) | **Yes** |
| `liquidity/` | Python 3.13 + web3 (own venv) | **Yes in retained code** — archived; service disabled and kill switch set |
| `executor/` | Python 3.13 + solders (own venv) | **Yes** — guarded Jupiter swaps (dry-run by default) |

Read `CLAUDE.md` before changing any of them; it carries the non-negotiables per
component.

---

## `ecosystem/` — paper orchestration and control room

The 0.4 package coordinates existing owners and serves the independent local UI.
It never starts a second recorder or changes a frozen research owner's version.

| Path | What it is |
| --- | --- |
| `ecosystem/cli.py` | Installed solecosystem command parser and dispatch |
| `ecosystem/runner.py` | Resumable paper pipeline coordination |
| `ecosystem/recovery.py` | Existing-owner and interrupted-pipeline recovery |
| `ecosystem/control.py` | Scoped paper actions and durable action receipts |
| `ecosystem/web.py` | Loopback control room and collector routes |
| `ecosystem/ui_service.py` | Verified UI checkpoint, manager binding and startup |
| `ecosystem/wiki.py` | Validated packaged documentation catalog and page reads |
| `scripts/build_ecosystem_wiki.py` | Offline public-document snapshot generator |
| `docs/ECOSYSTEM-WIKI.md` | Project wiki navigation and maintenance ownership |

## `oracle/` — observations and shadow evidence

Oracle 0.2.2 exposes instrument-bound observations, forecasts and history without
signing or submitting orders. Reference forecasts do not certify execution.

| Path | What it is |
| --- | --- |
| `oracle/cli.py` | Explicit source/archive CLI |
| `oracle/engine.py` | Observation and strategy evaluation owner |
| `oracle/store.py` | Historical observation archive |
| `oracle/reader.py` | Bounded read-only archive access |
| `oracle/server.py` | Read-only MCP tools and subscriptions |
| `oracle/guidance.py` | Source-linked consumer guidance |
| `oracle/voting.py` | Versioned source-labelled voting policy |

## `botmanager/` — persistent paper lifecycle and availability

Manager 0.7 reuses canonical simulation and existing evidence owners. The suite
runs the established Supervisor in process and starts or adopts a scoped UI.

| Path | What it is |
| --- | --- |
| `botmanager/src/botmanager/registry.py` | Shared command definitions and dispatch |
| `botmanager/src/botmanager/supervisor.py` | Fenced worker lifecycle and desired intent |
| `botmanager/src/botmanager/ledger.py` | Durable runtime/account state |
| `botmanager/src/botmanager/suite.py` | Availability supervision and bounded component alerts |
| `botmanager/src/botmanager/suite_service.py` | Fixed installed launchd/systemd user-service definitions |
| `botmanager/src/botmanager/machine_health.py` | Compact inert measurements and Prometheus rendering |
| `botmanager/src/botmanager/walkthrough.py` | Recommended complete command-stage walkthrough |
| `docs/bot-manager-managed-suite.md` | Installed operations and platform setup |

## `backtester/` — offline simulation

Event-driven backtester for spot and Jupiter-Perps-style leveraged strategies. Never
touches the network during a run; fetching is a separate explicit step.

Paths below are repo-relative, always — write backtester/core/gridsim.py rather than
core/gridsim.py. `scripts/check_docs.py` resolves every backtick-quoted path from the repo
root, so an abbreviated one fails the build.

| Path | What it is |
| --- | --- |
| `backtester/cli.py` | Entry point: `python3 -m backtester.cli` |
| `backtester/gridcli.py` | Entry point for the ladder-grid simulator, which owns its own bar loop |
| `backtester/botcli.py` | Entry point for the bot simulators: the DCA safety-order bot and the triangular-arbitrage replay over recorded quotes |
| `backtester/paircli.py` | Entry point for pairs/cointegration runs |
| `backtester/requirements.txt` | Declared deps, kept minimal on purpose |
| `backtester/README.md` | Scope, correctness priorities, usage |
| `backtester/PROMPT.md` | The prompt the component was built from |
| `backtester/strategy_cards/` | One card per registered strategy: equations, limitations, defaults |
| `backtester/tests/` | Unittest suites, including the research modules; counts in `docs/TESTING.md` |

### `backtester/core/` — the engine

| Path | What it is |
| --- | --- |
| `backtester/core/engine.py` | The bar loop. Owns the per-bar ordering that makes lookahead impossible |
| `backtester/core/types.py` | `BarWindow` (the structural lookahead guard), `CostConfig`, `RunManifest` |
| `backtester/core/indicators.py` | Trailing-window indicator functions, each returning a scalar for the current bar |
| `backtester/core/metrics.py` | Sharpe, drawdown, CAGR, with the conventions stated in the manifest |
| `backtester/core/perps.py` | Borrow-fee accrual and liquidation price for the perp mode |
| `backtester/core/gridsim.py` | Ladder-grid simulator; a port of `extension/src/core/grid.js` that must agree with it |
| `backtester/core/dcasim.py` | DCA safety-order bot simulator: base order, deeper safety orders, take-profit above the average entry; gridsim's bar order and pessimism |
| `backtester/core/trianglesim.py` | Triangular-arbitrage L1 replay: detect on one snapshot, execute at the quotes `latency_s` later; reads recorded snapshot files |
| `backtester/core/data.py` | `CsvLoader`, `SyntheticLoader`, bar validation, checksums |
| `backtester/core/fetch.py` | Explicit Coinbase OHLCV fetch into a local CSV cache; the engine stays offline |
| `backtester/core/fetch_minutes.py` | Resumable minute-bar cache fetch with rate limiting and coverage |
| `backtester/core/fetch_minutes_alt.py` | Minute bars from OKX/KuCoin/Bitget/WhiteBIT for coins Coinbase does not list |
| `backtester/core/ticks.py` | Explicit Coinbase trade-tick fetch and bar aggregation |
| `backtester/core/funding.py` | Signed Hyperliquid funding history, optional OKX cross-check |
| `backtester/core/archive_price.py` | Jupiter spot-price snapshot (this is what `data/JLP_spot.csv` is) |
| `backtester/core/cpcv.py` | Combinatorial purged cross-validation |
| `backtester/core/cointegration.py` | Cointegration tests for the pairs work |
| `backtester/core/pairs.py` | Pairs-trading construction |
| `backtester/core/universe.py` | Asset universe selection, with the survivorship-bias refusal |
| `backtester/core/report.py` | Run reports, walk-forward splits and manifest-last artifact hashes |
| `backtester/core/plotting.py` | Chart output |
| `backtester/core/strategy_cards.py` | Parses the cards and is checked against the registry both ways |
| `backtester/core/scorecard.py` | Compound five-minute scorecard: causal per-metric scores, family-deduped regime-weighted aggregate, veto gates, next-bar forecast statistics |
| `backtester/core/compound.py` | Backtests a scorecard configuration on 5m bars through the engine, in-sample vs out-of-sample, gaps split into segments |

### `backtester/core/strategies/` — the registry

| Path | What it is |
| --- | --- |
| `backtester/core/strategies/__init__.py` | `REGISTRY` (25 strategies), `FAMILY` taxonomy, `build()` |
| `backtester/core/strategies/signals.py` | Indicator-driven strategies, one screen each |
| `backtester/core/strategies/advanced.py` | The nine implemented from spec-only cards, incl. the Ichimoku displacement trap |
| `backtester/core/strategies/textbook.py` | DCA, EMA crossover, PPO, Fibonacci retracement and swing-confluence: the mechanisms the cited trading guides name (`tradingstrategyresults.json`) |
| `backtester/core/strategies/breakout.py` | Donchian channel breakout; the channel excludes the current bar |
| `backtester/core/strategies/ma_crossover.py` | The only strategy that can emit a short, and only when asked |
| `backtester/core/strategies/rsi.py` | RSI mean reversion |
| `backtester/core/strategies/buy_and_hold.py` | The baseline every other result is measured against |
| `backtester/core/strategies/composite.py` | Combines strategies under a `COMBINE_MODES` rule |

---

## `research/` — analysis on top of the backtester

The danger here is overstating a result, so the honesty machinery is the point.

| Path | What it is |
| --- | --- |
| `research/decide.py` | Per-bar readout: what every strategy, signal and indicator says about the last bar |
| `research/sweep.py` | Parameter sweeps |
| `research/cpcv_sweep.py` | CPCV sweep plus `interpret()`, which exists to kill the "lots of strategies work" misreading |
| `research/cross_asset_cpcv.py` | Whether a result on one coin transfers to another |
| `research/turnover_table.py` | One turnover pull shared by all ten coin spokes |
| `research/verify_numbers.py` | Re-derives every figure quoted in the research docs; exit 0 means they all check out |
| `research/full_suite.py` | One command: fetch fresh candles and funding for the universe, then the registry sweep and the compound 5m sweep on every asset |
| `research/geometry.py` | Grid geometry helpers |
| `research/perturb.py` | Parameter perturbation for robustness |
| `research/STRATEGIES.md` | The strategy survey |
| `research/RANKED_LISTS.md` | Ranked results |
| `research/TOP_COINS.md` | Coin shortlist |
| `research/TOP5-RECOMMENDATION.md` | The narrowed recommendation |
| `research/CROSS-ASSET-TRANSFER.md` | Cross-asset transfer findings |
| `research/PROMPT_STRATEGIES.md` | The prompt the strategy work was built from |
| `research/coin-intelligence/` | Ten per-coin spokes (BTC, ETH, SOL, BNB, XRP, TRX, HYPE, DOGE, ZEC, RAIN) plus a README |
| `research/results/` | Generated output; not source |

---

## `extension/` — the part that can place real orders

Chrome MV3 extension plus a CLI and a local HTTP API, all three thin adapters over one
command registry. No npm runtime dependencies by design; one vendored charting library
(`extension/vendor/lightweight-charts/`).

| Path | What it is |
| --- | --- |
| `extension/manifest.json` | MV3 manifest; validated in CI |
| `extension/package.json` | Scripts only — no runtime and no dev dependencies |
| `extension/README.md` | Includes the **Verification status** section; read it before extending |
| `extension/src/core/commands.js` | The single registry. Every action lives here or the parity test fails |
| `extension/src/core/risk.js` | Every risk rail, as a gate an order must pass. Rails fail closed |
| `extension/src/core/grid.js` | Ladder geometry. `backtester/core/gridsim.py` is its port |
| `extension/src/core/pnl.js` | FIFO/paired-lot attribution, fees included |
| `extension/src/core/engine.js` | The tick loop: reconcile, then plan |
| `extension/src/bg/service-worker.js` | MV3 service worker and its timer constraints |
| `extension/src/jupiter/http.js` | The HTTP layer for every Jupiter call |
| `extension/src/jupiter/trigger.js` | Trigger order API; the order-list response envelope is **guessed** |
| `extension/src/jupiter/price.js` | Price lookups |
| `extension/src/jupiter/attribution.js` | Fee attribution — **unconfirmed** against a real fill |
| `extension/src/venues/triggerVenue.js` | Venue adapter over the Trigger API |
| `extension/src/venues/index.js` | Venue selection |
| `extension/src/wallet/solana.js` | ~150 lines that make a Solana dependency unnecessary |
| `extension/src/wallet/signer.js` | Signing, and the session-key vault boundary |
| `extension/src/storage/store.js` | Storage interface |
| `extension/src/storage/fileStore.js` | Mode-0600 file store for secret material |
| `extension/src/storage/memoryStore.js` | In-memory store for tests |
| `extension/src/core/alerts.js` | Pure alert rules: only fresh, gated scout figures may say "act", backtest says "review", quoted APY is only a lead |
| `extension/src/market/holdings.js` | Read-only Base and Solana balances in USD; partial failures named, never zeroed |
| `extension/src/market/quote.js` | Swap quotes only: Jupiter Metis, and Slipstream on-chain CL math that refuses past the active range |
| `extension/src/market/pools.js` | DefiLlama yields, ranked by 30-day mean; every APY labelled quoted |
| `extension/src/market/net.js` | Read-only fetch and JSON-RPC; refuses any non-read method |
| `extension/src/ui/dashboard.js` | Signal Desk shell and hash router; four priority workflows and advanced views |
| `extension/src/ui/view-overview.js` | Overview and Alerts views |
| `extension/src/ui/view-markets.js` | Holdings, Profit & loss and Discover views |
| `extension/src/ui/view-trade.js` | Backtest & strategies and Swap views |
| `extension/src/ui/view-grid.js` | The experimental grid's forms, charts and journal |
| `extension/src/ui/popup.js` | Popup: signal/process glance, four workflow shortcuts and collapsed wallet/grid controls |
| `extension/tools/cli.js` | CLI surface over the registry |
| `extension/tools/api-server.js` | Local HTTP surface; reads `SMT_API_PORT`, `SMT_API_TOKEN`, `SMT_PASSPHRASE` |
| `extension/tools/dryrun.js` | The headless integration gate — a round trip must close positive |
| `extension/tools/verify-endpoints.js` | Live Jupiter reachability; reads `JUPITER_API_KEY` |
| `extension/tools/deps.js` | Dependency wiring |
| `extension/test/core.test.js` | Grid, risk, P&L, reconciliation, tick guards |
| `extension/test/surfaces.test.js` | Parity across the three surfaces |
| `extension/test/wallet.test.js` | Wallet and signing |

---

## `soltui/` — macOS menu-bar app and TUI

Read-only over the research side. Places no orders. Supervised by launchd, so the flag
file — not the menu-bar Quit item — is the real off switch.

| Path | What it is |
| --- | --- |
| `soltui/app.py` | The menu-bar app |
| `soltui/menubar_launcher.py` | Exists because py2app runs its target as a top-level script, which breaks relative imports; also `chdir`s to the repo |
| `soltui/tui.py` | Terminal UI |
| `soltui/shell.py` | v2 navigation over the TUI's panes: five destinations, health strip, Now overview builders, registry palette, Explain, theme (`docs/design/soltui-v2/DESIGN.md`) |
| `soltui/signals.py` | Signal derivation for display |
| `soltui/status.py` | Status model |
| `soltui/roster.py` | Watched-asset roster |
| `soltui/paper.py` | Paper positions |
| `soltui/runner.py` | The loop that refreshes state |
| `soltui/bgcontrol.py` | Explicit worker/fetch processes, lock handoff and nonce-bound socket Stop |
| `soltui/bgworker.py` | Detached offline sweep worker and per-process array cache |
| `soltui/compound.py` | Compound 5m tab backend: saved config, public live reads (Coinbase, Hyperliquid, RSS), forward-test ledger, sweeps; CLI `python3 -m soltui.compound` |
| `soltui/liquidity.py` | Reads daemon state; creates/removes only the KILL flag |
| `soltui/bots.py` | Five-bot list and Grid, Arbitrage, DCA and Trend settings, backtests, recorded-stream forward tests and gated optimization |
| `soltui/trend.py` | Long-only moving-average momentum paper bot; shared next-open engine with fees and slippage |
| `soltui/experiments.py` | Immutable experiment/cell SQLite evidence, typed search spaces, sparse observed heatmaps, TradingView import and comparison |
| `soltui/experiment_runner.py` | Frozen native bar/recorded-triangle evaluation, per-cell checkpoints, exploration exposure and fresh final holdout guards |
| `soltui/experiment_jobs.py` | Explicit background experiment processes, inherited leases, pause/cancel requests and interrupted-worker recovery |
| `soltui/experiment_screens.py` | Experiment workbench: typed search editor, explorer, observed maps, worker controls and CSV comparison |
| `soltui/pricefeed.py` | Streaming price recorder: stdlib WebSocket to Coinbase `level2_batch` + `ticker`, one-second gzip JSONL snapshots, detached process |
| `soltui/serve.py` | Optional loopback browser console |
| `soltui/bin/soltui` | Shell launcher with interpreter override |
| `soltui/config.py` | Configuration |
| `soltui/setup_app.py` | py2app build config (**alias** build, so the bundle references this checkout) |
| `soltui/make_icon.py` | Generates `SolTUI.icns` |
| `soltui/soltui-service` | `status` / `start` / `stop` / `build` / `install` for the launchd agent |
| `soltui/README.md` | Packaging traps already paid for — read before rebuilding |
| `soltui/tests/` | Unittest suites for models, rendering, workers, launchers and local controls |
| `soltui/tests/test_experiments.py` | Experiment store, search-space, sparse-map and external evidence regression tests |
| `soltui/tests/test_experiment_runner.py` | Frozen native evidence, holdout freshness, pause/cancel/resume and promotion recovery tests |
| `soltui/tests/test_experiment_interface.py` | Process leases/control races, registry refusals and live headless workbench interactions |

---

## `mongo/` — the local research store

A read-mostly MongoDB copy of everything the repo has measured (~29,000 documents in
the `solmargintrader` database), plus a runnable query reference. Derived: the files
on disk stay the source of truth, so the store can be dropped and rebuilt freely.
No other component imports the MongoDB loader.

| Path | What it is |
| --- | --- |
| `mongo/README.md` | Entry point: setup, collection map, question -> query index |
| `mongo/schema.py` | Collection specs, `$jsonSchema` validators, indexes. `--describe` needs no server |
| `mongo/load.py` | The loader. Drops and rebuilds, stamping provenance on every document |
| `mongo/requirements.txt` | `pymongo`, kept out of `backtester/requirements.txt` on purpose |
| `mongo/tests/test_load.py` | 20 tests: idempotency, provenance, strict validation, card semantics |
| `mongo/queries/01-coins-and-bars.js` | Price history, staleness, per-coin return, biggest drops |
| `mongo/queries/02-strategies-and-cards.js` | The inventory, warm-up cost, what is buildable next |
| `mongo/queries/03-signals-and-indicators.js` | Rule definitions and which mirror a strategy's defaults |
| `mongo/queries/04-decisions.js` | Per-bar readouts and where strategy families disagree |
| `mongo/queries/05-backtests.js` | Manifests, per-strategy metrics, drawdown, fills |
| `mongo/queries/06-experiments-and-pbo.js` | CPCV, sweeps, and PBO -- read this before any Sharpe |
| `mongo/queries/07-documents-and-search.js` | Full-text search over the write-ups |
| `mongo/queries/08-provenance-and-health.js` | Trace a number to a file; check the store is sane |

Three things about the shape, because they will come up:

- **Bars, spot prices and equity curves are native time series collections.** They
  accept no `$jsonSchema` validator and no unique index, which is exactly why
  `load.py` drops and rebuilds instead of upserting: nothing else would stop a
  second run from silently doubling every bar.
- **Strategy cards keep their own vocabulary.** `registry_key` is null for the 20
  cards that are not `Strategy` implementations, and that is not the same as
  "unimplemented" -- the ladder grid is `implemented` with no key because it is not a
  `Strategy` at all.
- **Every document carries provenance** (`source_path`, `source_sha256`,
  `loaded_at`), and bar series additionally carry `frame_checksum`, the identity a
  backtest manifest and a readout both print.

---

## Repository-level

| Path | What it is |
| --- | --- |
| `CLAUDE.md` | Agent instructions and the per-component non-negotiables |
| `AGENTS.md` | Points at `CLAUDE.md` |
| `GEMINI.md` | Gemini CLI equivalent |
| `.github/copilot-instructions.md` | Copilot CLI equivalent |
| `.github/workflows/ci.yml` | Extension, backtester, soltui, mongo, liquidity, executor and doc/index drift jobs |
| `CONTRIBUTING.md` | Contribution boundaries and validation workflow |
| `CODE_OF_CONDUCT.md` | Contributor conduct and reporting boundary |
| `docs/requirements.md` | Existing functional/runtime/safety requirements |
| `docs/MCP.md` | No repo MCP server; global connectors and offline fallback |
| `docs/caching-and-optimization.md` | Cache freshness and performance invariants |
| `docs/runbooks/incident.md` | Kill, preserve evidence, reconcile unknown outcomes |
| `docs/runbooks/rollback.md` | Revert code without discarding execution state |
| `docs/runbooks/handoff.md` | Prompt/memory/Git continuation workflow |
| `scripts/check_docs.py` | Fails the build on stale test counts or dead index entries |
| `docs/` | The documentation suite; `README.md` links every page |
| `data/` | Regenerable OHLCV cache — gitignored. Refetch with `backtester.core.fetch` |
| `results/` | Generated backtest output — not source |
| `.remember/remember.md` | Session handoff notes |

## `executor/` — guarded Solana swaps

Signs and sends real Jupiter swaps from the owner's Solana wallet behind a semantic verifier, rails, gates and a
journal. Dry-run by default. Agent rules: `executor/CLAUDE.md`.

| File | Role |
| --- | --- |
| `executor/README.md` | What it does, install, CLI/API surface |
| `executor/CLAUDE.md` | Non-negotiables, authorization limits, gaps |
| `executor/pyproject.toml` | Dependencies, CLI entry point, pytest and Ruff configuration |
| `executor/uv.lock` | Locked dependencies |
| `executor/src/executor/config.py` | `~/.executor/config.toml` (mode 600), rails and defaults, fail-closed validation |
| `executor/src/executor/tokens.py` | Token table, exact amount conversion; unknown tokens are refused |
| `executor/src/executor/jupiter.py` | Jupiter Swap v1 quote, swap build and Price API client |
| `executor/src/executor/quote.py` | Quote evaluation against the independent price reference |
| `executor/src/executor/lifi.py` | Cross-chain quote, quote only |
| `executor/src/executor/txverify.py` | Semantic transaction verifier: program allowlist, instruction decoding, balance deltas |
| `executor/src/executor/rails.py` | Every order rail, as code |
| `executor/src/executor/gates.py` | Dry-run soak and research gate, per strategy |
| `executor/src/executor/ledger.py` | Pure positions and realized P&L from the journal |
| `executor/src/executor/journal.py` | Append-only intent and result journal; unknown sends block |
| `executor/src/executor/signer.py` | Mode-600 key loading; the key is never printed |
| `executor/src/executor/rpc.py` | Solana JSON-RPC client; a send is never retried |
| `executor/src/executor/engine.py` | The swap pipeline shared by dry-run and live, and reconcile |
| `executor/src/executor/registry.py` | Command registry, response envelope, call log |
| `executor/src/executor/cli.py` | `executor` command line |
| `executor/src/executor/api.py` | Loopback HTTP API (bearer token, Origin refusal) |

## `liquidity/` — Aero Slipstream LP manager

Archived on 2026-11-08. The retained implementation can manage concentrated-liquidity
positions on Aero (Base) and sign transactions, but the service remains disabled with
its kill switch set. Do not reactivate it during setup or documentation work. Full detail: `liquidity/README.md`; agent rules:
`liquidity/CLAUDE.md`.

| File | Role |
| --- | --- |
| `liquidity/README.md` | How pools are judged, quick start, the daemon loop, safety |
| `liquidity/CLAUDE.md` | Owner's live-operation authorization and its limits |
| `liquidity/STATE_FILES.md` | `status.json` / `scout.json` / `KILL` contract with soltui |
| `liquidity/pyproject.toml` | Component dependencies, CLI entry point, pytest/Ruff configuration |
| `liquidity/uv.lock` | Locked component dependencies |
| `liquidity/src/aero_lp/chain.py` | Base RPC and Multicall3 read boundary |
| `liquidity/src/aero_lp/market.py` | GeckoTerminal transport/cache and income model helpers |
| `liquidity/src/aero_lp/providers.py` | Read-only provider comparison and source labels |
| `liquidity/src/aero_lp/validation.py` | Shared finite-number validation for liquidity safety configuration |
| `liquidity/src/aero_lp/config.py` | TOML risk/custody/configuration boundary |
| `liquidity/src/aero_lp/state.py` | Daemon state directory and state-file writes |
| `liquidity/src/aero_lp/wallet.py` | Mode-0600 key file / Keychain loading; never print its output |
| `liquidity/src/aero_lp/metrics.py` | Every profitability measure for one pool |
| `liquidity/src/aero_lp/scout.py` | Candidate discovery and ranking |
| `liquidity/src/aero_lp/allocator.py` | Pure deploy / experiment / graduation decisions |
| `liquidity/src/aero_lp/ledger.py` | SQLite P&L ledger |
| `liquidity/src/aero_lp/submissions.py` | Durable owner-bound transaction journal; unresolved submissions block new writes |
| `liquidity/src/aero_lp/recovery.py` | Receipt-based idempotent ledger recovery and historical slot attribution |
| `liquidity/src/aero_lp/daemon.py` | The loop: manage, compound, scout, allocate, status |
| `liquidity/src/aero_lp/executor.py` | Transaction sequences; `SimRunner` (eth_simulateV1) and `LiveRunner` |
| `liquidity/scripts/aero-lp-service` | launchd install / status / kill / resume |
| `.claude/agents/aero-pool-scout.md` | Read-only research agent that second-guesses the scout |

### Audit and continuation references

| Path | What it is |
| --- | --- |
| `docs/repo-bootstrap-audit-2026-11-06.md` | Standards audit, changes and explicit remaining infrastructure gaps |
| `docs/code-deep-optimizer-2026-11-06.md` | Bounded code audit, regressions, review dissent and verification limits |
| `docs/optimization-workbench.md` | Use the optimization workbench, understand provenance and final holdout limitations |
| `docs/optimization-workbench-plan.md` | Six-feature implementation plan, interfaces, ownership and acceptance criteria |
| `docs/code-optimizer-scope-2026-11-06.json` | Primary/dependency source scope and every remaining source path |
| `docs/jupiter-trigger-contract.md` | Public API contract fixtures and blocked live-signing boundary |
| `docs/COMPOUND-5M.md` | Compound five-minute scorecard: how a call is made, every metric, what else is checked, measured findings |
| `docs/COMPOUND-5M-PAPER.md` | Paper on the compound scorecard: every metric (what it checks, why it is included), every tunable parameter, protocol and results recomputed from the saved sweep, threats to validity |
| `docs/TRADINGVIEW-REFERENCE.md` | TradingView Advanced Charts docs distilled for this repo: indicator parity with the backtester, built-in study catalog, PineJS Std functions, datafeed and marks contracts, drawings API, Broker API concepts, licensing limits, Agent Skills format |

### Not source

`build/`, `dist/`, `jup.ag/`, `jup.ag.zip`, `pagesource/` and `tradingskilllist` are
captured artifacts and scratch material. Nothing imports them; do not treat them as
part of any component.

## Dashboard workspace

| Path | Purpose |
| --- | --- |
| `extension/src/ui/workspace-model.js` | Registry workspace groups, structured result tables, chart points and safe CSV conversion. |
| `docs/EXTENSION-TUI-PARITY.md` | Browser workflows, native-session lifetime, execution boundaries and verification. |

## Live prediction display

| Path | Purpose |
| --- | --- |
| `soltui/live_score.py` | Current forward-vote eligibility, latest call snapshot and terminal tick-window layout. |
| `extension/src/ui/live-score.js` | Browser score adapter and aligned immutable price/score tick chart. |
| `docs/LIVE-PREDICTION-SCORE.md` | Scoring, eligibility, freshness and observation-history contract. |

### Signal Desk interface

| Path | Purpose |
| --- | --- |
| `extension/src/ui/signal-desk.js` | Real-data workflow composition, local run comparisons, pinned paper drafts, evidence dialogs and read-only refresh lifecycle. |
| `extension/src/ui/desk-model.js` | Pure compatibility, source snapshot, eligibility explanation and archived-control presentation contracts. |
| `extension/src/ui/signal-desk.css` | Accessible light/dark Signal Desk tokens, responsive layouts, dense mode and popup styling. |
| `soltui/desk.py` | Loaded-array research provenance and exact paper handoff validation; no worker starts or network. |
| `docs/SIGNAL-DESK.md` | UI workflows, persistence, provenance boundaries and use instructions. |

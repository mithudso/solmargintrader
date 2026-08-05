# Codebase overview

A file map for orientation, grouped by directory. Every path here is checked by
`scripts/check_docs.py`, so a rename that is not reflected below fails the build.

Four components, in ascending order of how much damage a bug can do:

| Component | Language | Can it move money? |
| --- | --- | --- |
| `research/` | Python 3.13 | No — analysis over the backtester |
| `soltui/` | Python 3.13 | No — read-only display |
| `backtester/` | Python 3.13 | No — simulation only, by design |
| `extension/` | JavaScript (ESM, no deps) | **Yes** |

Read `CLAUDE.md` before changing any of them; it carries the non-negotiables per
component.

---

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
| `backtester/paircli.py` | Entry point for pairs/cointegration runs |
| `backtester/requirements.txt` | Declared deps, kept minimal on purpose |
| `backtester/README.md` | Scope, correctness priorities, usage |
| `backtester/PROMPT.md` | The prompt the component was built from |
| `backtester/strategy_cards/` | One card per registered strategy: equations, limitations, defaults |
| `backtester/tests/` | 454 tests (`unittest`), including the research modules |

### `backtester/core/` — the engine

| Path | What it is |
| --- | --- |
| `backtester/core/engine.py` | The bar loop. Owns the per-bar ordering that makes lookahead impossible |
| `backtester/core/types.py` | `BarWindow` (the structural lookahead guard), `CostConfig`, `RunManifest` |
| `backtester/core/indicators.py` | Trailing-window indicator functions, each returning a scalar for the current bar |
| `backtester/core/metrics.py` | Sharpe, drawdown, CAGR, with the conventions stated in the manifest |
| `backtester/core/perps.py` | Borrow-fee accrual and liquidation price for the perp mode |
| `backtester/core/gridsim.py` | Ladder-grid simulator; a port of `extension/src/core/grid.js` that must agree with it |
| `backtester/core/data.py` | `CsvLoader`, `SyntheticLoader`, bar validation, checksums |
| `backtester/core/fetch.py` | The only network path: Coinbase OHLCV into a local CSV cache |
| `backtester/core/archive_price.py` | Jupiter spot-price snapshot (this is what `data/JLP_spot.csv` is) |
| `backtester/core/cpcv.py` | Combinatorial purged cross-validation |
| `backtester/core/cointegration.py` | Cointegration tests for the pairs work |
| `backtester/core/pairs.py` | Pairs-trading construction |
| `backtester/core/universe.py` | Asset universe selection, with the survivorship-bias refusal |
| `backtester/core/report.py` | Run reports and walk-forward split output |
| `backtester/core/plotting.py` | Chart output |
| `backtester/core/strategy_cards.py` | Parses the cards and is checked against the registry both ways |

### `backtester/core/strategies/` — the registry

| Path | What it is |
| --- | --- |
| `backtester/core/strategies/__init__.py` | `REGISTRY` (25 strategies), `FAMILY` taxonomy, `build()` |
| `backtester/core/strategies/signals.py` | Indicator-driven strategies, one screen each |
| `backtester/core/strategies/advanced.py` | The nine implemented from spec-only cards, incl. the Ichimoku displacement trap |
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
command registry. Zero runtime dependencies by design.

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
| `extension/src/ui/dashboard.js` | Dashboard view |
| `extension/src/ui/popup.js` | Popup view |
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
| `soltui/signals.py` | Signal derivation for display |
| `soltui/status.py` | Status model |
| `soltui/roster.py` | Watched-asset roster |
| `soltui/paper.py` | Paper positions |
| `soltui/runner.py` | The loop that refreshes state |
| `soltui/config.py` | Configuration |
| `soltui/setup_app.py` | py2app build config (**alias** build, so the bundle references this checkout) |
| `soltui/make_icon.py` | Generates `SolTUI.icns` |
| `soltui/soltui-service` | `status` / `start` / `stop` / `build` / `install` for the launchd agent |
| `soltui/README.md` | Packaging traps already paid for — read before rebuilding |
| `soltui/tests/` | 95 tests (~70s) |

---

## Repository-level

| Path | What it is |
| --- | --- |
| `CLAUDE.md` | Agent instructions and the per-component non-negotiables |
| `AGENTS.md` | Points at `CLAUDE.md` |
| `GEMINI.md` | Gemini CLI equivalent |
| `.github/copilot-instructions.md` | Copilot CLI equivalent |
| `.github/workflows/ci.yml` | Extension, backtester, soltui and doc-drift jobs |
| `scripts/check_docs.py` | Fails the build on stale test counts or dead index entries |
| `docs/` | The documentation suite; `README.md` links every page |
| `data/` | Regenerable OHLCV cache — gitignored. Refetch with `backtester.core.fetch` |
| `results/` | Generated backtest output — not source |
| `.remember/remember.md` | Session handoff notes |

### Not source

`build/`, `dist/`, `jup.ag/`, `jup.ag.zip`, `pagesource/` and `tradingskilllist` are
captured artifacts and scratch material. Nothing imports them; do not treat them as
part of any component.

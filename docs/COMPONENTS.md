# Components

What each module is for, what it exposes, and what it depends on. `docs/codebase-overview.md`
is the flat file map; this page is the shape of the thing.

The eleven components have explicit ownership boundaries. `backtester/` supplies the
canonical simulation package to research and headless runtimes. Oracle supplies
source-labelled observations and forecasts. Bot Manager owns specifications,
account state and paper lifecycle; ecosystem coordinates existing research owners
and serves the control room. These responsibilities do not require MongoDB.

The extension and SolTUI communicate through framed native messages rather than
sharing runtime code. Their trading paths retain independent gates. The executor
has its own guarded Solana execution boundary. Liquidity is retained for reference
and remains disabled with its kill switch set.

---

## `botmanager/`

The standalone manager 0.7 separates durable specifications, typed defaults,
command dispatch and SQLite persistence. Grid, DCA, Trend and Momentum paper
workers reuse the packaged canonical simulator and source-bound evidence. Reads
do not initialize an absent data home. Research, reporting, learning, backup and
legacy controls preserve their established owners and evidence gates.

The availability suite runs the existing Supervisor in process. It starts or
adopts the UI only after verifying its manager home, ecosystem home, generation,
version, lock and HTTP identity. Compact health and Prometheus measurements remain
separate from rich account status and trading readiness. See
[managed-suite operations](bot-manager-managed-suite.md).

## `ecosystem/`

The 0.4 package coordinates F5, prospective paper trials, Oracle archives and Bot
Manager through their existing owners. The independent loopback control room uses
scoped durable actions; it stays separate from pipeline execution. The packaged
wiki preserves authoritative source text and provenance. The manual Jupiter V2
path provides unsigned previews; submit remains blocked pending independent
semantic economic verification. See [control-room operations](ECOSYSTEM-CONTROL-ROOM.md).

## `oracle/`

Oracle 0.2.3 owns instrument-bound observations, shadow forecasts and historical
evidence. Its MCP surface exposes read-only tools and subscriptions. Reference
prices, vote agreement and receipt freshness remain distinct from executable
quotes, source certification and profit. The forecast service never signs or
submits orders. A separately enabled TradingView worker can dispatch Coinbase
spot orders through the authenticated official CLI, or locally constructed GUM
ZEC perpetual Actions through an explicitly configured owner signer. Durable
per-leg intents, account reconciliation and ambiguity holds gate that path;
dry-run remains the default. See [Oracle integration](bot-manager-oracle-interface.md)
and [Jupiter ZEC execution](JUPITER-ZEC-WEBHOOK.md).

## `executor/`

The optional executor owns guarded Solana spot execution through its separate
virtual environment. Rails, semantic transaction verification and an append-only
submission journal gate that path. Unknown submissions cannot be retried as if
absent. Dry-run remains the default. Read `executor/CLAUDE.md` before changes.

---

## `backtester/`

### `core/engine.py` — the bar loop

The single place execution ordering is decided, and the reason lookahead is structurally
impossible rather than merely avoided. Per bar, in this order: accrue borrow fees, execute
a fill scheduled for this bar at this bar's **open**, check liquidation against this bar's
range, ask the strategy for a target using data `<= i` only, then schedule the resulting
order for `i + fill_delay`.

```python
run_backtest(strategy, arrays, config) -> BacktestResult
```

`EngineConfig` carries mode, leverage, `fill_delay` (default 1 — the conservative choice),
`rebalance_threshold` and costs. `BacktestResult.exposure` is the **applied** exposure
(signed notional over equity), not the raw target — a distinction that matters to anything
comparing against it.

**Depends on:** `types`, `metrics`, `perps`. No I/O, no network.

### `core/types.py` — the lookahead guard

`BarWindow` is the guard. A strategy receives only this object, every accessor truncates at
bar `i`, and reading past `i` raises `LookAheadError`. Also `CostConfig` (fees, slippage,
borrow rates in **bps per hour** to sidestep the venue's deci-bps ambiguity), `Position`,
`Trade`, and `RunManifest` — everything needed to reproduce a run byte-for-byte.

### `core/strategies/` — the registry

```python
REGISTRY: dict[str, Callable]   # 25 strategies, name -> factory
FAMILY: dict[str, str]          # taxonomy: trend, mean-reversion, regime-filter, ...
build(name, **params) -> Strategy
```

Factories rather than instances, because several strategies carry state and a shared
instance would leak position state between runs. A strategy implements
`warmup_bars()` and `on_bar(history) -> float`, returning a target exposure in `[-1, 1]`
for the **next** bar.

Adding one requires a module plus one `REGISTRY` entry — no engine change — **and** a
`strategy_cards/<id>.md` in the same commit, whose machine-readable half is checked against
the code in both directions.

### `core/indicators.py`

Trailing-window functions, each returning a scalar for the current bar rather than a
series — strategies are called once per bar, so a series would be wasted work and would
invite indexing the wrong position. Exponential recursions use a capped lookback
(`EMA_CAP_MULTIPLE = 12`, chosen for a measured 2.4e-13 relative error) and a smaller
warm-up multiple (`EMA_WARMUP_MULTIPLE = 3`).

### `core/gridsim.py` — the ladder grid

Separate from the exposure engine and deliberately so: the extension's edge comes from
limit orders filling *intrabar* at known prices, which a target exposure cannot express.
Own bar loop, own entry point (`backtester.gridcli`).

**This module is a port of `extension/src/core/grid.js`.** A change to either one's
economics needs the matching change in the other, or the backtest becomes a confident
wrong number about the live strategy. Do not confuse it with the `grid` strategy in
`core/strategies/signals.py`, which is an exposure staircase, not a ladder of resting
orders.

### `core/data.py` and `core/fetch.py`

`CsvLoader` and `SyntheticLoader` both satisfy one `DataLoader` protocol, so tests need no
network. `validate_bars` checks schema, ordering and gaps; `checksum_frame` makes a run
traceable to its input. The explicit fetch modules write caches: Coinbase bars/minutes/ticks/products, Jupiter
spot snapshots and signed funding history. The simulation engine never fetches.

---

## `research/`

### `decide.py` — the per-bar readout

What every strategy, signal and indicator says about the last cached bar.

```python
replay_targets(strategy, arrays, *, mode, allow_short) -> np.ndarray
decide_strategy(key, arrays, ...) -> StrategyDecision
build_report(arrays, *, asset, interval, ...) -> dict
```

Strategies are replayed bar-by-bar from the start of history, because several are
path-dependent: a Donchian position opened on a breakout stays long through bars whose own
close would never have opened it. It imports the engine's own `_resolve_target` rather than
reimplementing the clamp, and its test suite asserts parity against a recording wrapper
around `run_backtest`.

### `cpcv_sweep.py` — and why `interpret()` exists

Combinatorial purged cross-validation over the strategy space. `interpret()` turns four
numbers into the reading a person should take from them, specifically to catch two
dangerous misreadings: a high positive-count with a high PBO ("lots of strategies work!"),
and a low PBO with a low positive-count. It has its own test file.

### `verify_numbers.py`

Re-derives every figure quoted in the research documents. Exit 0 means the prose matches
the code. This is the component's honesty gate — `research/`'s failure mode is overstating
a result, and this is what makes that detectable.

---

## `extension/`

### `src/core/commands.js` — one registry, three surfaces

Every action lives here. The Chrome message handler, `tools/cli.js` and
`tools/api-server.js` are thin adapters over it, and `test/surfaces.test.js` fails the
build if any surface drifts. Do not add a handler, CLI branch or HTTP route carrying its
own logic.

### `src/core/risk.js` — the rails

Every rail is a gate an order must pass. Two properties matter more than the list: a rail
documented but not enforced here is not a rail, and rails **fail closed** — a missing or
NaN state field must not silently disable one (see `normaliseState`).

### `src/core/engine.js` — reconcile, then plan

The venue's live order list is the source of truth at the top of every tick; local state is
a cache. An intent submitted but not found live becomes `unknown` and is **never**
auto-retried — that is exactly how a rung double-fires after a crash.

### `src/core/grid.js` and `pnl.js`

Ladder geometry and FIFO/paired-lot attribution. `grid.js` owns `expectedRoundTripUsd`,
which exists because the "exit at the level you bought at" bug shipped once: it captures
zero and pays two fees. Both files stay free of I/O and `chrome.*`.

### `src/jupiter/http.js`

The single HTTP layer: 4 attempts, full-jitter exponential backoff, a token-bucket request
budget charged **per attempt** so a retry storm cannot bypass it, 15s per-attempt timeout.
See `docs/external-calls.md`.

### `src/storage/`

Three implementations of one interface — `store.js` (IndexedDB: intents, fills, carry,
events), `fileStore.js` (mode-0600, for secret material), `memoryStore.js` (tests). The
intent journal is what makes the bot restart-safe: an intent is written before it is
submitted.

### `src/wallet/solana.js`

~150 lines that make a Solana dependency unnecessary, including the base58 zero-byte case.
Do not add a package to solve what this already solves.

---

## `mongo/`

A derived MongoDB store plus a runnable query reference. Full detail in
`mongo/README.md`.

`schema.py` holds the collection specs, `$jsonSchema` validators and indexes, and
`describe()` prints the layout with neither a server nor the driver present. `load.py`
builds every document and inserts it.

```python
schema.create(db, drop=True)                              # collections, validators, indexes
load.build_all(only=None, run_suites=False) -> dict[str, list[dict]]
```

Two constraints drive the design. **Time series collections accept no unique index**, so
there is no upsert key for a bar — `load.py` drops and rebuilds instead, and
`mongo/tests/test_load.py` asserts two consecutive loads leave identical counts, because
nothing else would catch a second load silently doubling every bar. And **every document
carries provenance**, because a figure that cannot be traced back to a file is not a
figure; that is the same reason `RunManifest` exists.

`decisions` documents are `research.decide.build_report()` output verbatim rather than a
Mongo-specific shape, so the store and the readout cannot disagree about what a strategy
said.

## `soltui/`

macOS menu-bar app plus a TUI and headless research runtime. Research remains
paper-only. Manual Coinbase spot orders use a separately armed path; manual Jupiter
V2 submit remains blocked pending independent economic verification.

- `app.py` is the menu-bar app; `tui.py` the terminal UI; `signals.py`, `status.py`,
  `roster.py`, `paper.py` the display model.
- `menubar_launcher.py` exists because py2app runs its target as a top-level script, which
  breaks relative imports — and because a Finder or launchd launch starts at `/`, so it
  `chdir`s to the repo before `data_dir="data"` is resolved.
- `setup_app.py` is an **alias** build, so the bundle references this checkout and must be
  rebuilt if the repo moves. Never install a bundle built from a worktree — the worktree
  gets deleted and login startup breaks silently.
- `commands.py` is the one registry of every console action; `tui.py`, `cli.py`
  (`soltui call|list`), `api.py` (`soltui api`, loopback + bearer token) and `native_host.py` (Chrome
  native messaging, installed by `native_host_install.py`) all call `dispatch()` and return the same
  envelope. `liquidity.resume` is `requires_confirm`; keep the archived liquidity service disabled.
  Manual order commands retain their separate confirmation and arming gates. `presets.py` turns the Top 5 into
  one-click presets (`top5.presets`), `netpct.py` is the one net % definition and `pnl.py` the pure P&L maths
  behind `pnl.summary|series|breakdown`; `wallet.py` is the read-only wallet
  scan (`portfolio.scan`, `wallet.key_sources`): public endpoints only, no key, no signing; `hdwallet.py` (BIP32
  public derivation, address encoders, private-key refusal), `utxo_scan.py` (xpub scans of BTC, LTC, DOGE),
  `eth_scan.py` (Ethereum mainnet), `spot_prices.py` and `portfolio.py` (snapshots, `portfolio.changes`, the
  notice line) extend it; `portfolio_agent.py` installs the hourly `com.mitchhudson.soltui.portfolio` LaunchAgent.
- `soltui-service` is the operational surface: `status`, `start`, `stop`, `build`,
  `install`.

---

## `liquidity/`

Archived on 2026-11-08. The retained Aero Slipstream liquidity manager on Base
contains live-capable code, but its service remains disabled and its kill switch
set. Full detail in `liquidity/README.md`; do not reactivate it during onboarding.

```python
metrics.evaluate_pool(chain, market, pool, deposit_usd) -> PoolMetrics   # income, LVR, edge, model + backtest APR
scout.run_scout(chain, market, deposit_usd, out=path) -> dict            # ranked scout.json
allocator.plan_allocation(pools, idle_usd, deployed_usd, cfg) -> AllocationPlan
Rebalancer.rebalance / withdraw / deploy / topup / claim / collect       # every on-chain sequence
Daemon(cfg, live, signer).run()                                          # the loop
```

Three constraints shape it:
- **Income is measured, never quoted.** Fees come from `feeGrowthGlobal` deltas and AERO from the gauge's
  reward share. A volume × fee estimate overstated fee income about 5× on the pool where it was checked.
- **A pool must clear the bar twice.** The forward model and a replay of the pool's actual price path must
  both beat `min_net_apr`. When candidates are close, the daemon runs a side-by-side experiment instead of
  guessing.
- **Every on-chain sequence goes through one `Rebalancer` with a `Runner`.** Dry-run therefore simulates with
  `eth_simulateV1` exactly what live mode would sign. soltui never imports any of it; it reads the state files.

## `website/` — hosted accounts and public research

The website 0.4.0 source has no runtime npm dependencies. Wrangler is pinned
development tooling. Static files under `website/public/` provide the workspace,
wallet sign-in, membership controls, paper-first bot builder, research reader,
customer connections and separate agent/managed-bot authorization settings. Source version does not prove deployment.

| Path | API and ownership |
| --- | --- |
| `website/src/worker.js` | Cloudflare API: wallet accounts/sessions, tenant-owned configurations, verified Stripe membership and protected analysis proxy |
| `website/src/oauth.js` | Public-client PKCE S256, exact resource/redirect binding, separately wallet-signed trading policy, scoped credentials and revocation |
| `website/src/mcp.js` | Stateless authenticated MCP 2025-11-25 JSON POST; status and trade tools always derive the wallet from the bearer grant |
| `website/src/trades.js` | Atomic policy/entitlement reservations, customer-owned preparation/submission, authoritative reconciliation and ambiguous-outcome retention |
| `website/src/managed-bots.js` | Dedicated signed bot authority, immutable strategy/connection binding, per-bot leases and exactly-once fill allocation |
| `website/src/backtest-jobs.js` | Durable owned jobs, request/result binding and terminal-receipt quota reconciliation |
| `website/src/billing-lifecycle.js` | Explicit plan previews/commit, pending-payment upgrades, renewal downgrades and safe cancellation/release |
| `website/src/account-lifecycle.js` | Durable deletion fence and verified private credential erasure |
| `website/execution/` | Private customer Coinbase executor, encrypted credentials, exact previews, inventory/policy/plan admission and venue reconciliation; Jupiter remains gated |
| `website/public/agent-access.js` | Explicit agent consent, finite preauthorization and grant revocation; no per-trade approval prompt |
| `website/migrations/` | Additive D1 account, subscription/usage, OAuth grant/token and trade-intent schema |
| `website/api/openapi.json` | Account, billing, OAuth and MCP HTTP contracts |
| `website/engine/runtime.py` | Dedicated public-data/native Oracle lifecycle, immutable calculation inputs and verified checkpoint restoration |
| `website/runtime/` | One Cloudflare Container owner and epoch-fenced R2 checkpoints; paid entitlement and actual deployment acceptance remain separate gates |
| `website/scripts/export_research.py` | Deterministic tracked research/card publication with source hashes and bounded body shards |
| `website/scripts/smoke.mjs` | Explicit deployed-wallet account creation and deletion acceptance |
| `website/README.md` | Setup, storage, billing, deployment and outstanding activation boundaries |
| `website/docs/MCP-DESIGN.md` | Wallet-bound preauthorization, supported protocol and customer execution qualification limits |

Starter renews at $9.99/month for three configured slots and ten backtests per
UTC day. Advanced is $29.99/month for ten slots and unlimited backtests.
Unlimited is $49.99/month without subscription count caps. The first eligible
subscription has a seven-day trial. Risk and resource bounds remain on every
plan. Checkout defaults closed until its launch gates qualify.

Agent trading consent signs one finite policy with venues, assets, USD caps and
expiry; subsequent trade calls do not ask for wallet approval again. Consent
cannot create delegated signing authority. `LIVE_EXECUTION_ENABLED` defaults
to `false`, and no `USER_TRADE_EXECUTOR` is provisioned. Successful adapter
fixtures do not establish a real connection, signer, venue reconciliation or order.

The engine accepts allow-listed market parameters, not arbitrary paths or code.
It needs dedicated public data caches and an approved Oracle archive. The
backtest response retains default model costs and limitations; it does not
certify a customer’s venue fee tier, supported market or future profit. Local
ladder, pair and event runners remain separate. Wallet identity, subscription
entitlement, live data and venue execution are distinct capabilities.

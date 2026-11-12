# Architecture

Ten components have explicit execution boundaries. Backtester, research, the Oracle
forecast service, Bot Manager and ecosystem automation do not place orders. The
separately enabled Oracle TradingView worker can submit Coinbase spot orders or
GUM ZEC perpetual Actions. The extension and optional
executor retain separately gated live-capable paths. SolTUI has a separately armed
manual Coinbase path. Liquidity contains live-capable code but is archived, disabled
and killed. MongoDB is derived research storage, never an execution dependency.

The separate hosted `website/` package serves wallet accounts, public research and
inactive paper bot definitions. A Cloudflare Worker serves static assets and API
routes; D1 owns account/session/subscription data. Stripe and a separately provisioned
read-only Python analysis adapter are outbound integrations. The website cannot control
the owner's local suite or submit orders. Billing, analysis and live execution remain
independent capability gates. See [the website guide](../website/README.md).

```
browser ──HTTPS──▶ website Worker ──▶ D1 accounts and paper definitions
                       ├──────────▶ Stripe subscription API
                       └──HTTPS───▶ read-only Python analysis adapter
                                          ├──▶ canonical backtester
                                          └──▶ selected Oracle archive
```

The standalone raw-event capture support tool writes a durable event spool and uploads
to a dedicated MongoDB time-series namespace. It does not use `mongo/load.py`'s
drop/rebuild ownership or replace the existing sampled recorder. See
[its command boundary](SCRIPTS.md#bounded-raw-event-capture).

The standalone `botmanager/` application exposes the `solbot` command registry and owns
its bot specifications and a fenced paper runtime. Each account
keeps separate virtual capital, lots, cursor and generation. A versioned local
backtester package supplies canonical offline economics. The supervisor and service
lifecycle are explicit; reads start nothing. Legacy operations, research evidence
and raw recording retain their existing owners. Bounded Coinbase sampled-midpoint
replay does not certify Jupiter execution. The manager cannot sign or submit live orders.

```
backtester/            research/              extension/
  core/fetch.py  ──▶ data/            core/commands.js ◀── bg/service-worker.js  (Chrome)
  core/engine.py       sweep.py         │                ◀── tools/cli.js          (CLI)
  core/strategies/     STRATEGIES.md    │                ◀── tools/api-server.js  (HTTP)
  ▼                    ▼                ▼
  results/             research/results/  core/engine.js ──▶ venues/ ──▶ Jupiter API
```

## Managed availability and evidence owners

The manager 0.7 suite holds one per-home lease and runs the existing Supervisor
in process. Lifecycle generations, desired bot intent and account evidence remain
with that Supervisor. The suite starts a verified control room or adopts an owner
with the same manager home, ecosystem home and package identity. It retains only
actual child-process handles as termination authority; an adopted PID is diagnostic.

Ecosystem 0.4 coordinates F5 and prospective trials without replacing their queue,
recording or evidence ownership. Oracle 0.2.3 owns source-labelled shadow forecasts
and archives. Availability does not create a recorder, research authority, optimizer,
signer or P&L ledger. Existing frozen environments remain attached to their owners.

Collector measurements distinguish suite, manager, control room and market-data
freshness. Server readiness requires the first three; market certification and order
permission stay separate. The wiki is a validated public-document snapshot, not a
runtime probe. See [managed-suite operations](bot-manager-managed-suite.md) and
[wiki ownership](ECOSYSTEM-WIKI.md).

## TradingView execution boundary

`oracle/webhook.py` accepts a bounded, authenticated TradingView payload and stores
it durably before replying. Forecast votes do not veto an accepted webhook.
`oracle/webhook_orders.py` binds the journal to its execution mode and venue;
`oracle/gum_webhook_orders.py` records each close/open leg before one submission.
A missing or ambiguous fill blocks another open. Opposite-side signals require a
full reduce-only close, flat-position read-back and settled collateral first.

`oracle/gum_orders.py` checks ZEC market/account identity, integer lots, fees,
collateral and price bounds before signing a locally constructed Jupnet Action.
The optional private signer verifies its configured owner. It never signs an
upstream opaque transaction. GUM app funding, perps collateral deposits and order
Actions are separate operations; the order verifier does not prove a deposit safe.
See [the account and execution contract](JUPITER-ZEC-WEBHOOK.md).

## Extension

### Module map

| Path | Responsibility |
| --- | --- |
| `src/core/grid.js` | Pure grid engine: levels, side selection, paired exits, planning, capital |
| `src/core/risk.js` | Risk rails and batch admission. Fails closed |
| `src/core/pnl.js` | FIFO lot matching, snapshots, equity curve, drawdown, CSV |
| `src/core/engine.js` | The tick: reconcile → ingest fills → plan → admit → place |
| `src/core/commands.js` | The command registry — every action, transport-agnostic |
| `src/jupiter/http.js` | Retry, backoff, `Retry-After`, per-attempt budget, per-attempt timeout |
| `src/jupiter/price.js` | Price and decimals, tolerant of two response shapes |
| `src/jupiter/trigger.js` | Trigger V2: auth, vault, deposit craft, create, manage |
| `src/venues/index.js` | `VenueAdapter` contract, dry-run wrapper, read-only Perps |
| `src/venues/triggerVenue.js` | The one live-capable adapter |
| `src/wallet/solana.js` | base58, shortvec, signature insertion — no `@solana/web3.js` |
| `src/wallet/signer.js` | Null / pending-approval / session-key signers, encrypted vault |
| `src/storage/store.js` | IndexedDB journal + `chrome.storage` config |
| `src/storage/fileStore.js` | The same interfaces on JSON files, for CLI and API |
| `src/bg/service-worker.js` | Alarms, badge, message plumbing. No strategy logic |
| `src/ui/` | Popup and dashboard. Equity chart via vendored Lightweight Charts (`charts.js`, SVG fallback); ladder chart hand-built SVG; CSP-safe |

`core/grid.js`, `risk.js` and `pnl.js` take no I/O and no `chrome.*`. That is what makes the strategy
unit-testable and lets the same code run under `node --test`, in the CLI, and in the browser.

### The tick

Order of operations is the design. **Reconcile before plan, always.**

1. **Price** — refuse a non-finite or non-positive price outright. A NaN price would flow into P&L,
   get persisted as the daily realized figure, and permanently poison the daily-loss rail.
2. **Reconcile** — fetch live orders and match them to journal intents by `(side, level±1bp)`.
   Exact price equality is unsafe: `intentKey` rounds to `level × 1e6`, so a venue echoing `69.2384`
   for our `69.238424` yields a different key. Each intent backs at most one live order.
3. **Ingest fills** — idempotent by venue order id. Quantity comes from the fill or its intent, never
   from current config, so editing `notionalPerRungUsd` cannot rewrite history.
4. **Plan** — exits from open lots (one rung up), entries at levels below the market not already
   holding a lot.
5. **Admit** — every candidate through the rails, applied incrementally.
6. **Place** — write the intent as `submitting` **before** the network call, then promote or fail it.

### Restart safety

Solana has no client-order-ID primitive, and an MV3 service worker can be killed at any moment —
including between "write the intent" and "the venue accepted the order". Two mechanisms:

- **Write-ahead journal.** An intent is persisted as `submitting` before the network call, so a
  worker that dies mid-submit leaves a record.
- **Reconcile as truth.** An intent marked `submitting` that is not live becomes `unknown` and is
  **never auto-retried** — auto-retry is precisely how a rung double-fires. Live orders with no
  journal entry are adopted so they occupy cap space.

The tick also records the **actual wake delta**, because Chrome silently clamps short alarm periods
and an unnoticed clamp makes a live run behave unlike its dry run.

### The venue seam

```
getPrice · getDecimals · getOpenOrders · getFills · getCarryCosts · placeOrder · cancelOrder
```

| Adapter | State |
| --- | --- |
| `TriggerVenue` | Live-capable. Spot. Trigger V2 returns signable transactions over HTTP |
| `DryRunVenue` | Wraps any adapter: real prices and real code paths, simulated fills, zero writes |
| `PerpsVenueReadOnly` | Extension adapter refuses writes. It does not implement the separate GUM Beta order API used by the Oracle worker |

Fills in dry run are modelled **pessimistically** — each rung fills at its trigger price moved
against us by the full slippage allowance. An optimistic simulator makes a losing grid look
profitable.

### Why the grid earns anything

Each exit rests **one rung above** the lot it closes, so gross per round trip equals the rung width.
Assigning sides purely by comparing each level to the current price looks equivalent and is not: a
level whose bid just filled gets an offer at that same price as soon as the market gaps below it,
capturing zero and paying two fees. That bug shipped once;`expectedRoundTripUsd` plus a test asserting
`gross === notional × rungWidth` keep it fixed.

**Lot linkage.** The planner pairs each exit to specific lots and records them on the exit intent
(`lots`). `ingestFills` copies them onto the sell fill as `closesLots`, and `pnl.js` closes those lots
first. This matters because the planner reads its exits off the residual open lots: with strict FIFO,
rung B's exit filling before rung A's consumed A and left B's lot as the "residual", so the next plan
rested a sell at the level the real inventory was bought at — zero spread, two fees. Linkage keeps the
residual equal to the inventory actually held, and makes realized P&L (and so the daily-loss rail) the
P&L of the lot actually sold. Paired matching is the default for `snapshot` and `matchFifo`. Strict
FIFO (`{ linkage: false }`, the tax-style convention) is available but unused by the live path. Fills
stored before linkage have no `closesLots` and still match FIFO. `gridsim.py` mirrors this
(`RestingOrder.closes`).

## Backtester

Event-driven, offline, and deliberately separate. Explicit fetch modules (`fetch.py`, `fetch_minutes.py`, `ticks.py`, `universe.py`,
`funding.py`, `archive_price.py`) touch the network; it writes a local CSV cache that `core/engine.py` reads. Strategies live in
`core/strategies/` behind a registry, so adding one does not touch the engine. Spot and
Jupiter-Perps-style leveraged modes share the engine, with the borrow fee modelled in the P&L path
rather than bolted on.

**Two execution models, on purpose.** `core/engine.py` runs `Strategy` objects, which map history to
one target exposure filled at a bar boundary. `core/gridsim.py` runs the resting-ladder grid — the
extension's strategy — whose edge comes from limit orders filling *intrabar* at known prices, which
a target exposure cannot express. It owns its own bar loop and its own entry point
(`backtester.gridcli`), and it ports `extension/src/core/grid.js` function for function so the
backtest and the live strategy agree on what a round trip earns. Keeping them separate is deliberate:
folding the ladder into the exposure engine would imply the two are comparable on the same axis.

Its correctness priorities — no lookahead, costs always applied, honest reporting of a losing
strategy — are documented in `backtester/README.md` and enforced by 1081 tests.


## Companion components

- **Research** imports the backtester and operates on cached data. Explicit data-preparation
  commands can delegate to fetch modules; simulation and strategy readout remain offline.
- **Soltui** displays research results and paper positions and exposes separately
  armed manual Coinbase controls. Manual Jupiter V2 submission remains blocked.
  Its background controls can explicitly start a data fetch or a sweep subprocess. The Liquidity tab reads `status.json` and `scout.json`;
  it never imports the executor or signs. Its kill/resume control writes/removes only the
  liquidity KILL flag. The archived service must remain disabled and killed.
  The optional browser console binds loopback.
- **MongoDB** imports research/backtester definitions and rebuilds selected derived collections.
  It is not imported by an execution component. Loading is destructive to the selected derived
  collections; tests prove repeat-load idempotency.
- **Liquidity**, archived and disabled, has its own virtualenv and one `Rebalancer`/`Runner` execution seam. `SimRunner`
  performs `eth_simulateV1`; `LiveRunner` signs and sends. Pure strategy and allocator decisions
  remain separate from RPC/market I/O. The daemon writes a SQLite ledger and state files for soltui.

## Recorded architecture decisions

1. **Keep simulation separate from execution.** The backtester never gains a live submit path.
   Explicit fetches write caches. A backtest only reads those caches.
2. **Share commands across extension surfaces.** Chrome messages, CLI and HTTP invoke the same
   registry. Their parity test detects extra handlers or missing routes.
3. **Mirror ladder economics, not runtime code.** Python gridsim and JavaScript grid code retain
   separate engines with matching rung/lot economics and regression tests.
4. **Use existing retrieval tools.** `index/build.py` owns offline metadata/text/concept indexes;
   `scripts/build_doc_index.py` derives the short retrieval map from the overview. Semantic
   embeddings are optional and explicit, not a startup requirement.

## soltui command bridge

`soltui/commands.py` is the single registry for everything the console can do. The TUI, `soltui call`,
`soltui api` and the Chrome native-messaging host (`soltui/native_host.py`, reached by the extension's
`soltuiCall` command) all call `dispatch(name, params, surface)`. The extension shares no code with Python;
the framed JSON protocol of the native host is the only coupling. Research/replay commands remain
simulations. Manual Coinbase/Jupiter order commands retain their separate reviewed live-order gates.
`liquidity.resume` (deleting the aero-lp `KILL` file) also needs `confirm`. Dashboard leases retain one
multiplexed host while a dashboard is open; bounded long-call workers leave status and cancellation
available. Native-session activity defers extension auto-reload. See `docs/EXTENSION-TUI-PARITY.md`.

## Optimization experiment evidence

The Bots experiment workbench uses a local SQLite store for immutable full specifications and
per-candidate/coin/window results. The native runner binds code, data, costs and temporal windows
before evaluation, then commits each cell. The job controller launches explicit subprocesses with
inherited file leases, durable pause/cancel controls and interrupted-state recovery. The shared
command registry serves the TUI, CLI and API.

Exploration exposes train/validation only. Final validation freezes one training-selected candidate
and reserves unused temporal intervals before evaluating it against the baseline. Both exploration
exposure and final reservations survive search-context changes. Sealed final history can enter later
exploration, while remaining spent for other final tests; active unsealed reservations stay protected.
Legacy evidence is fenced
conservatively. Freshness covers recorded local optimization history, not unknown external use.
Imported TradingView evidence preserves units and provenance, receives compatibility diagnostics,
and has no native promotion path. See [the guide](optimization-workbench.md).

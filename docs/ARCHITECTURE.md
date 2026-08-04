# Architecture

Two independent systems that share a subject (SOL) and nothing else. There is no code path from the
backtester into the extension: research does not place orders, and the extension does not simulate.

```
backtester/            research/              extension/
  core/fetch.py  ──▶ data/            core/commands.js ◀── bg/service-worker.js  (Chrome)
  core/engine.py       sweep.py         │                ◀── tools/cli.js          (CLI)
  core/strategies/     STRATEGIES.md    │                ◀── tools/api-server.js  (HTTP)
  ▼                    ▼                ▼
  results/             research/results/  core/engine.js ──▶ venues/ ──▶ Jupiter API
```

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
| `src/ui/` | Popup and dashboard. Hand-built SVG charts, CSP-safe |

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
| `PerpsVenueReadOnly` | Writes throw `NotImplemented` with the concrete next step. Jupiter has no public REST write API for Perps |

Fills in dry run are modelled **pessimistically** — each rung fills at its trigger price moved
against us by the full slippage allowance. An optimistic simulator makes a losing grid look
profitable.

### Why the grid earns anything

Each exit rests **one rung above** the lot it closes, so gross per round trip equals the rung width.
Assigning sides purely by comparing each level to the current price looks equivalent and is not: a
level whose bid just filled gets an offer at that same price as soon as the market gaps below it,
capturing zero and paying two fees. That bug shipped once;`expectedRoundTripUsd` plus a test asserting
`gross === notional × rungWidth` keep it fixed.

**Known attribution limitation:** the planner pairs each exit to a specific lot, but realized P&L
matches FIFO (tax-correct). With several rungs open these disagree — portfolio totals are right,
per-round-trip figures follow FIFO. Add lot linkage on the fill record if you need per-rung
attribution.

## Backtester

Event-driven, offline, and deliberately separate. `core/fetch.py` is the only component that touches
the network; it writes a local CSV cache that `core/engine.py` reads. Strategies live in
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
strategy — are documented in `backtester/README.md` and enforced by 141 tests.

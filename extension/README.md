# SolMarginTrader

A Chrome MV3 extension that runs a **grid trading strategy on Jupiter (Solana)** with hard risk
rails and full P&L tracking. **Dry-run by default** — it will not place an order until you change
the mode and type a confirmation.

> **Not financial advice.** Grid trading is a short-volatility strategy: it makes money in a
> range and loses money in a trend. Any leveraged position can be liquidated. In the included dry
> run, a simulated 24% drawdown leaves the grid **−$8.62 on $48 of deployed capital** with four
> open lots and no closed round trips — that is what a grid does in a one-way move. Trade only
> capital you can lose entirely.

---

## Two findings that changed the design

**1. The downloaded site copy does not contain Jupiter's code.**
`../jup.ag/` is a 16-file rendered-HTML dump (~42 MB) from the "Website Downloader" extension.
It has **zero `.js` bundles** — it references `https://jup.ag/assets/index-*.js` and friends, but
never downloaded them. So the premise "should have all of the code it runs" does not hold.

What it *was* good for: confirming the intended venue (the saved root page is
`jup.ag/perps/long/SOL-SOL.html`), extracting real token mints (SOL, USDC, USDT, JUP, jupSOL,
jupUSD), and showing the site bundles `vendor-anchor-*.js` — a hint that on-chain interaction is
built client-side with Anchor rather than driven by a REST API.

**2. Jupiter Perps has no public REST write API.**
Jupiter's own docs, checked live on 2026-08-04:

> **WARNING** — The Perps API is still a **work in progress**, stay tuned!

with a pointer to Anchor IDL parsing of the perps program. Opening or closing a leveraged position
therefore requires building Anchor instructions and going through the keeper request/fulfil flow —
not something to ship inside a service worker on a first pass.

So the **executable** venue is the **Trigger V2 API**, which does return signable transactions over
HTTP. A grid is a ladder of resting limit orders, which is precisely what Trigger is for. It also
keeps pending orders **off-chain**, so your ladder is not a public roadmap for front-runners — a
real advantage over the V1 on-chain PDA model.

Both venues sit behind one `VenueAdapter` interface, so Perps drops in when its API ships.

---

## Install

```bash
cd ~/dev/solmargintrader/extension
npm test              # 96 tests, no dependencies to install
node tools/dryrun.js  # end-to-end tick against the live SOL price
```

Then load it in Chrome:

1. `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select `~/dev/solmargintrader/extension`
3. Open the extension → **Dashboard & settings** → set your grid, then **Save**

Chrome 137+ is recommended: full-auto signing uses WebCrypto Ed25519, which landed in 137.
Everything else works from Chrome 120.

---

## Modes, and what each one can actually do

| Mode | Places orders | Signing | Unattended |
|---|---|---|---|
| `dry-run` *(default)* | No — simulated fills | Never signs | Yes |
| `semi-auto` | Yes | You approve every signature | **No** |
| `full-auto` | Yes | Dedicated session key | Yes |

**Why three modes and not one:** an injected browser wallet (Phantom et al.) cannot produce a
silent signature, and `window.solana` does not exist in a service worker at all. "Unattended bot"
and "wallet popup per trade" are mutually exclusive. A single "live" mode would have to quietly
pick one, so both are named instead.

`dry-run` is not a mock: it uses the real price feed, the real grid engine, the real risk rails and
the real journal. Only the fills are simulated, and they are simulated **pessimistically** — every
rung fills at its trigger price moved against you by the full slippage allowance, because an
optimistic simulator makes a losing grid look profitable.

---

## Key custody

`full-auto` is the only mode where a key exists in the browser. The rules it follows:

- Use a **dedicated keypair** holding only grid working capital. Never your main wallet.
- At rest the 32-byte seed is **AES-GCM** encrypted under a passphrase-derived key
  (**PBKDF2-SHA256, 600,000 iterations**), with a fresh 16-byte salt and 12-byte IV per
  encryption. Same plaintext never produces the same ciphertext — there is a test for that.
- It is stored in `chrome.storage.local` **only**. Never `.sync`, which would upload it to Google.
- The decrypted seed exists only inside a signing call, is never logged, never stringified, and
  never crosses a message boundary.
- A wrong passphrase fails closed and does not distinguish "wrong passphrase" from "tampered
  record".
- The Jupiter API key gets the same `.local`-only treatment and is cleared from the DOM after save.

One custody fact you should know and cannot change: Trigger V2 deposits go into a **Privy-managed
custodial vault**, one per wallet. Funds for resting orders sit there, not in your wallet. Getting
them back from an unfilled order is a two-step cancel-and-withdraw.

---

## Risk rails

All enforced in `src/core/risk.js` as a gate every order must pass. A rail that lives only in a
README is not a rail.

| Rail | Default | What it stops |
|---|---|---|
| `killSwitch` | off | Latching hard stop; a stray "arm" cannot resume trading |
| `maxTotalNotionalUsd` | 500 | Total capital at risk across all rungs |
| `maxNotionalPerOrderUsd` | 100 | One fat-fingered rung |
| `maxConcurrentOrders` | 12 | Ladder sprawl |
| `maxLeverage` | 1 | Leverage creep |
| `dailyLossLimitUsd` | 50 | Halts the engine for the UTC day when realized P&L hits it |
| `maxSlippageBps` | 300 | Getting filled at a terrible price |
| `minLiquidationDistancePct` | 25 | Perps only; ignored when the venue reports no liquidation price |
| `maxOrdersPerTick` | 4 | Rate-limit blowout on a cold start |

Batch admission applies caps **incrementally**, so six orders that each pass the per-order cap
cannot collectively breach the total cap. There is a test for that too.

---

## How restart-safety works

Solana has no client-order-ID primitive, and an MV3 service worker can be killed at any moment —
including between "write the intent" and "the venue accepted the order". Two mechanisms handle it:

1. **Write-ahead journal.** An intent is persisted with status `submitting` *before* the network
   call. A worker that dies mid-submit leaves a record.
2. **Reconcile before plan, every tick.** The venue's live order list is the source of truth; local
   state is only a cache. An intent marked `submitting` that is *not* live becomes `unknown` and is
   **never auto-retried** — auto-retry is exactly how you double-fire a rung after a crash. Live
   orders with no journal entry are adopted so they occupy cap space.

Rung identity is derived from `(gridId, side, level)`, the only things the venue echoes back.

The tick also records the **actual wake delta**. Chrome silently clamps short alarm periods, and a
clamp that goes unnoticed makes a live run behave unlike its dry run.

---

## Leverage — read this before setting it above 1

Trigger V2 is a **spot** venue. Setting `leverage: 3` on it does not create leverage. Rather than
trade unleveraged while the config claims 3x, the worker **refuses to tick** and logs why.

Real leverage needs one of:

- **Jupiter Perps** — native leverage, blocked on the missing write API described above.
- **Jupiter Lend borrow** — borrow against collateral, grid the borrowed size, and track the borrow
  rate as a carry cost. **Not implemented** (see stubs below).

The P&L module never assumes a funding rate. Carry costs are passed in explicitly, because
Jupiter perps charges a borrow rate against the pool rather than a symmetric CEX-style funding
payment between longs and shorts — hardcoding the latter would be a silent lie in your numbers.

---

## How the grid actually earns its spread

Each exit rests **one rung above** the lot it closes, so the gross captured per round trip equals
the rung width. This sounds obvious and is easy to get wrong: assigning each level a side purely by
comparing it to the current price means a level whose bid just filled gets an *offer at that same
price* as soon as the market gaps below it. That round trip captures zero and still pays two fees.
The first working version of this file had exactly that bug; `expectedRoundTripUsd()` and a test
asserting `gross === notional × rungWidth` exist to keep it fixed.

Consequently:

- Bids are placed at levels below the market that do not already hold a lot
- Every sell is the paired exit of a specific buy, derived from open lots — never from a level's
  position relative to the market
- Only the bids need funding up front; each becomes the inventory backing its own exit

**Known attribution limitation.** The planner pairs each exit to a specific lot, but realized P&L
matches **FIFO** (tax-correct, see below). When several rungs are open at once these disagree: an
exit intended to close the $85 lot may be matched against an older $98 lot instead. Portfolio-level
totals are right either way; per-round-trip figures reflect FIFO, not the intended pairing. If you
need per-rung strategy attribution, add lot linkage on the fill record.

## P&L accounting

Realized P&L uses **FIFO lot matching** — the IRS default for property and what crypto tax tools
expect, so the CSV export reconciles.

- Entry fees ride on the lot, so a partial close realizes only its proportional share
- Unrealized is net of entry fees still sitting on open lots
- Carry costs are subtracted from realized P&L and folded into the equity curve at their own
  timestamps
- A sell with no lot behind it is surfaced as `unmatchedSellQty`, never silently dropped
- Equity curve, max drawdown (dollars and % of peak), win rate, total fees, CSV export

A worked case from the test suite: buy 1 @ $100 (fee $0.50), sell 1 @ $110 (fee $0.55) →
gross $10.00, fees $1.05, **net $8.95**; with $2.00 carry, **realized $6.95**.

---

## Three surfaces, one registry

Every action lives in `src/core/commands.js` (22 commands). The Chrome message handler, the CLI and
the HTTP API are thin adapters over it, so anything you can do in the UI you can script — and
`test/surfaces.test.js` fails the build if any surface drifts.

```bash
node tools/cli.js                                   # all commands, auto-generated help
node tools/cli.js <command> --help                  # arguments and types
node tools/cli.js setConfig --lower 60 --upper 90 --rungs 7 --notionalPerRungUsd 12
node tools/cli.js levels                            # rung ladder + gross per round trip
node tools/cli.js plan --price 75                   # what it WOULD place; places nothing
node tools/cli.js arm && node tools/cli.js tick --count 3
node tools/cli.js pnl --json
```

```bash
node tools/api-server.js --port 8787                # prints a bearer token
curl -s -H "Authorization: Bearer $SMT_API_TOKEN" http://127.0.0.1:8787/v1/commands
```

The API is loopback-bound, requires a bearer token compared in constant time, allows `GET` only for
read-only commands, and refuses any request carrying `Origin` or `Sec-Fetch-Site` — a web page *can*
post to localhost, so a token alone would not be enough.

Useful CLI flags: `--json` for machine output, `--ephemeral` for throwaway in-memory state, and
`--store-path` / `--config-path` to isolate a run. An unknown flag is rejected rather than ignored;
a silently dropped `--notionalPerRungUsd` would be a money bug.

Full reference: [../docs/API.md](../docs/API.md).

---

## Layout

```
manifest.json              MV3 manifest, minimal permissions (storage, alarms + 3 Jupiter hosts)
src/core/grid.js           Pure grid engine — levels, side selection, planning, capital needs
src/core/risk.js           Risk rails and batch admission
src/core/pnl.js            FIFO matching, snapshots, equity curve, drawdown, CSV
src/core/engine.js         The tick: reconcile -> ingest fills -> plan -> admit -> place
src/core/commands.js       The command registry — every action, transport-agnostic
src/jupiter/http.js        Retry/backoff, Retry-After, request budget, per-attempt timeout
src/jupiter/price.js       Price API, tolerant of both response shapes
src/jupiter/trigger.js     Trigger V2: auth, vault, deposit craft, create, manage
src/venues/index.js        VenueAdapter contract, dry-run wrapper, read-only Perps
src/venues/triggerVenue.js The live-capable adapter
src/wallet/solana.js       base58, shortvec, signature insertion (no web3.js dependency)
src/wallet/signer.js       Null / pending-approval / session-key signers + encrypted vault
src/storage/store.js       IndexedDB journal + chrome.storage config
src/storage/fileStore.js   The same interfaces on JSON files, for the CLI and API
src/bg/service-worker.js   Alarm scheduling, message plumbing, badge
src/ui/                    Popup and dashboard (hand-built SVG charts, CSP-safe)
tools/cli.js               CLI surface, generated from the registry
tools/api-server.js        Local HTTP API surface, generated from the registry
tools/dryrun.js            Headless end-to-end tick
test/                      96 tests, zero dependencies (node:test)
```

No build step and no dependencies. Plain ESM modules load directly as an unpacked extension —
`@solana/web3.js` would have added a megabyte to a service worker for base58 and one signature
insertion, so those are ~150 lines in `src/wallet/solana.js` instead, with tests against real mints.

---

## Verification status

**Done and proven:**

- `npm test` → **96 passing, 0 failing** (unit, integration and three-surface parity)
- `node tools/dryrun.js --ticks 8 --osc 6 --offline 100` → full tick loop with a down-then-up path:
  4 bids placed, filled as price fell, exits placed one rung above each lot, and on tick 8 an exit
  filled and took net P&L from −$2.33 to **+$0.04**. The closed trip captured **$0.620**, which is
  exactly `$12 notional × 516.7 bps rung width` — the economic contract holding end to end.
- `node tools/dryrun.js --ticks 4 --walk 5 --offline 100` → trending case: 4 bids placed, all 4
  fill as price falls to $85, no exit fills, net **−$3.90**. Correct for a one-way move, and the
  reason `--osc` exists. At the deeper trough of the oscillating run (price $76, −24%) the same
  grid sits at **−$8.62** with four open lots and no closed round trips.
- Price endpoint verified live with `curl` (keyless `lite-api.jup.ag/price/v3` → 200, SOL $73.64)
- Trigger V2 request/response shapes transcribed from the live docs, with client-side validation
  mirroring the documented server rules
- Ed25519 signing and the encrypted vault round-trip are covered by real WebCrypto tests

**Bugs caught and fixed during development:**

1. **Zero-spread exits** — the planner offered at the level it had just bought at. Gross zero, two
   fees paid, every cycle a loss. Fixed with the paired-exit model above.
2. **base58 phantom leading zero** — `base58Encode` returned 33 characters for 32 zero bytes and
   `base58Decode` returned 33 bytes for an all-`1` string, from a seeded `[0]` digit. That is the
   system-program / uninitialised-pubkey case.
3. **Reconciliation matched on exact price equality** — `intentKey` rounds to `level * 1e6`, so a
   venue echoing `69.2384` for our `69.238424` produced a different key, orphaning a live order and
   re-planning the same rung. That is a double-fire. Matching is now tolerant to 1 bp, and a test
   feeds real `normaliseOrders()`-shaped input (no `intentKey`, 4-decimal price) through
   `reconcile()` to assert one journal entry, not two.
4. **Fill quantity derived from current config** — editing `notionalPerRungUsd` would retroactively
   rewrite historical fill sizes. Quantity now comes from the fill or its intent, and a fill with
   neither is refused and surfaced rather than guessed.
5. **XSS-shaped table rendering** — journal rows interpolated venue-supplied order IDs and error
   strings into `innerHTML` behind a hand-rolled escaper, on a page holding extension privileges.
   Rows are now built with `createElement`/`textContent`.
6. **`window.prompt()` as the live-arm gate** — Chrome suppresses modal dialogs in an extension
   popup, so the confirmation would silently no-op or close the popup. Replaced with an inline
   typed confirmation.

**Not verified — do these before risking money:**

1. **No live order has been placed.** The write path (auth → vault → deposit craft → sign →
   create) is written to the documented shapes but never executed. It needs a Jupiter API key and a
   funded wallet. Test with one rung at the $10 minimum.
2. **Order-list response envelope.** `normaliseOrders()` guesses field names for the
   orders/history endpoint. Reconciliation depends on `triggerPriceUsd` and fill fields, so verify
   against a real response and correct the mapping.
3. **Fee attribution.** Fills currently take `feeUsd` from the venue when present and 0 otherwise.
   Zero fees make a grid look better than it is — confirm where Trigger reports fees.
4. **Chrome alarm floor.** 30s is assumed; the engine logs the real wake delta. Watch it before
   trusting a sub-minute tick.
5. **Transaction signature insertion** is tested against synthetic transactions, not a real
   Jupiter deposit transaction.

**Deliberately stubbed, each throwing a message that says how to finish it:**

- `PerpsVenueReadOnly` — all methods throw `NotImplemented` with the concrete next step
  (decode position accounts via `getProgramAccounts` + the perps IDL)
- Jupiter Lend borrow as a margin source — `leverageFeasibility()` refuses and explains
- `PendingApprovalSigner` queues transactions but the dashboard has no approval UI yet, so
  `semi-auto` currently queues and reports `PendingApproval` rather than completing an order
- OCO/OTOCO bracket bodies exist in the client but the grid only emits `single` orders

---

## Legal and operational notes

- This integrates via Jupiter's **documented public APIs**, not by automating the jup.ag UI.
  Scraping or driving the frontend would be brittle and a worse ToS position. Review the
  [Jupiter SDK/API License Agreement](https://developers.jup.ag/docs/legal/sdk-api-license-agreement)
  before running this against real funds.
- Trigger V2 requires an API key for every call, and rate limits apply per tier. The client
  implements backoff and a request budget, but a tight tick across many rungs will still find the
  ceiling.
- Automated trading may have tax and reporting consequences. Every fill is a disposal; the CSV
  export exists for that reason.
- Minimum order size is **$10**, so a 7-rung grid needs meaningful capital before it is even legal
  on the venue. The dashboard computes the requirement for your configuration.

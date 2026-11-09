# SolMarginTrader

A Chrome MV3 extension for the owner's Base and Solana money: **holdings, profit and loss, pool
discovery, backtests and strategy changes, swap quotes, and alerts** when a more profitable pool or
strategy appears. It also keeps an **experimental grid trading strategy on Jupiter (Solana)** with
hard risk rails, on its own tab, **dry-run by default** — it will not place an order until you
change the mode and type a confirmation. The grid lost to buy-and-hold walk-forward on 9 of 9 coins,
which is why 0.3.0 moved it off the front page.

## Dashboard workspace (0.4.0)

The dashboard now exposes the complete installed SolTUI registry in workspaces for Now, Signal,
Research/replay, Bots/prices, Experiments, Money/orders, Library/editor, TUI settings and Archive.
The popup's **Full workspace** link opens it. Forms include explicit true/false values; results
include sortable/filterable tables, CSV/JSON exports, time-series charts, row detail and guarded
catalogued-document editing. Manual order previews hand off to explicitly confirmed submit forms.
Signal has a read-only recorder chart and saved forward predictions. Native sessions retain replay
and running-job state while a dashboard is open; status and cancellation remain usable during long
calls. See [dashboard workflows, lifecycle and verification](../docs/EXTENSION-TUI-PARITY.md).

## Existing market views

| Tab | Source | Label it carries |
| --- | --- | --- |
| Overview | The stored alert scan, then a live holdings read | — |
| Holdings | Base: JSON-RPC `eth_getBalance` + ERC-20 `balanceOf` in one batch (chain id checked, 8453), prices from DefiLlama. Solana: Jupiter's holdings read (`lite-api.jup.ag/ultra/v1/holdings`), Solana RPC as fallback, prices from Jupiter Price v3. LP positions from the aero-lp daemon via soltui `liquidity.data` | `live`, `partial`, `failed` per chain |
| Profit & loss | soltui `pnl.summary` / `pnl.series`; simulated and real sections are never summed | `real money` / `simulated` |
| Discover pools | Aero scout (`liquidity.data`: modelled net APR from measured fee growth and gauge share) first; DefiLlama yields (`yields.llama.fi/pools`) second | `modelled` / `quoted` |
| Backtest & strategies | soltui `top5.list`, `roster.*`, `backtest.run`, `strategies.history`, `signals.*` | `backtest` |
| Swap | Solana: Jupiter Metis quote. Base: Aero Slipstream pools read on chain (exact CL math inside the active tick range; refused past it) | quote only — you sign on jup.ag or aerodrome.finance |
| Alerts | `scanAlerts` (periodic alarm, default hourly): a scouted pool beating a position or idle Base stablecoins above its break-even deposit, a new Top 5 leader or one beating the active strategy, quoted pool leads | `modelled` → worth acting on (only when the scout is under 48 h old, backtest-positive, medium/high confidence and unflagged), `backtest` → review, `quoted` → lead (no notification unless asked) |
| Grid | Unchanged engine, rails and journal | `experimental` |

**Swaps are quote-only.** The extension builds and signs no swap transaction; the bundled signer has
no semantic transaction verifier (Stele KNOW-837). **Quoted APYs never raise an "act" alert**:
`liquidity/CLAUDE.md` forbids treating a quoted APR as income (Stele KNOW-838). The public Solana RPC
answers HTTP 403 to any request carrying a `chrome-extension://` Origin, which is why Solana balances
come from Jupiter's holdings read in the browser; the CLI and API fall back to RPC when Jupiter fails.

**Live signing gate:** the bundled signer does not yet verify the economic intent of
remote-crafted deposit/withdrawal transactions. Trigger live writes therefore refuse
automatic signing, even with a session key and live confirmation. Dry-run works. A trusted
semantic-verification bridge and validated live fixtures are required before enabling
those writes; see `../docs/jupiter-trigger-contract.md`.

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
npm test              # unit and parity tests; no dependencies to install
node tools/dryrun.js  # end-to-end tick against the live SOL price
```

Then load it in Chrome:

1. `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select `~/dev/solmargintrader/extension`
3. Open the extension → **Dashboard & settings** → set your grid, then **Save**

Chrome 137+ is recommended: full-auto signing uses WebCrypto Ed25519, which landed in 137.
Everything else works from Chrome 120.

**Did a reload pick up the new code?** The popup header and the dashboard title show the
manifest version (`v0.4.0`). Every change to `src/` or `manifest.json` bumps it, in
`manifest.json` and `package.json` together; CI fails a pull request that changes either
without a bump, and `test/version.test.js` keeps the two fields equal. The SolTUI console
is the primary dashboard workspace (popup → **Full workspace**).

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
   **never auto-retried** — auto-retry is exactly how you double-fire a rung after a crash. `tick()`
   holds every `unknown` rung out of planning and re-centring (result reason
   `unknown-intent-needs-review`, key list in `unknownIntents`) until a fill arrives or a human runs
   `resolveIntent --intentKey <key> --confirm`. Live
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

**Lot linkage.** The planner pairs each exit to specific lots (`lots` on the exit intent) and the
sell fill records them as `closesLots`. P&L closes those lots first, so the residual `planGrid` and
`recentreDecision` read is the inventory actually held, and realized P&L (including the daily-loss
rail) is that of the lot actually sold. Without this, an exit for the $90 lot filling before the
$100 lot's exit would consume the $100 lot under FIFO and leave a phantom $90 lot, whose exit would
then rest at $100: zero spread. Fills stored before linkage have no `closesLots` and fall back to
FIFO.

## Auto re-centring — opt-in, and narrower than it sounds

`lower`/`upper` are static config, so a ladder can end up nowhere near the market. The stock
defaults are 60–90; on the real SOL daily series that band is outside the market on **87.3% of
bars**. `autoRecentre` lets `planGrid` move the ladder to `0.85x–1.15x` of price — the same
convention `tools/dryrun.js` uses, so there is only one.

It is **off by default** and a fresh install behaves exactly as it did before it existed. To turn it
on, and to see what it would do before arming anything:

```bash
node tools/cli.js setConfig --autoRecentre true --recentreSpanPct 0.15
node tools/cli.js plan          # reports `recentre`; computes only, places nothing
```

`setConfig` range-checks both values, because `ConfigStore.setConfig` is a blind merge — an
out-of-range span would otherwise not surface until it threw inside every tick, which fails closed
but bricks the grid silently instead of refusing the input.

**`recentreDecision()` refuses far more often than it acts, and the refusals are the feature.**
Moving the bounds changes every level, and a level is what an order's identity and a lot's paired
exit are derived from:

| Refusal | Why |
| --- | --- |
| `open-lots-would-be-stranded` | An open lot's exit is derived from the *current* levels. Re-centre downward while holding inventory and that lot's sell is recomputed onto the new, lower ladder — **below its own entry**. That is the zero-spread bug above, except now it realizes a loss. Counted, not summed, so a `NaN` quantity cannot read as flat. |
| `resting-orders-would-be-stranded-and-tick-cannot-cancel` | `tick()` has **no cancel step** — `cancelOrder` is a manual command. A moved ladder would leave real orders live at abandoned levels with capital committed to a ladder the strategy no longer believes in. |
| `price-inside-ladder` | Nothing to fix. `recentreDriftBps` adds slack beyond the bounds first. |
| `auto-recentre-disabled`, `unusable-price`, `already-centred` | Off; no usable price; would be a no-op. |

So it can only act on a grid holding nothing with nothing resting. **Measure it before believing
it helps:**

```bash
node tools/measure-recentre.js --csv ../data/SOL_1d.csv
```

On SOL daily (1,875 bars) it fires **exactly once, on the first bar** — because once bids rest they
stay resting, and if they fill there is a lot. And the honest result is that on this path it made
placement **worse**: one inception-time re-centre locked the ladder onto the 2021 price of $39.25
(→ 33.36–45.14) and the market left it behind, giving **93.1%** of bars outside the ladder versus
**87.3%** for the untouched 60–90 default.

Read that as what it is. The value here is *not* return; it is that a grid armed today starts with a
ladder around today's price instead of a hardcoded band. Tracking the market after that needs a
cancel path in `tick()`, which is a change to the order lifecycle and is not this.

And to keep it in proportion: at the time of writing (2026-08-04) SOL is **$74.03**, which the stock
60–90 ladder already contains, so `autoRecentre` would return `price-inside-ladder` and change
nothing at all. Turning it on is not a decision with much upside; leaving it off costs nothing.

The moved bounds are **persisted before any order is placed** (`engine.js`), for the same reason the
intent journal is written before the network call. `planGrid` is pure, so an uncommitted re-centre
would vanish: the next tick would see the new orders resting, refuse to re-centre, fall back to the
old bounds and place a **second ladder** at the levels this tick just abandoned. There is a test.

## P&L accounting

Realized P&L closes the lots each sell was **paired** with (`closesLots`), then falls back to **FIFO**
for anything unlinked (legacy fills, unmatched sells). The planner, `recentreDecision` and the
daily-loss rail all use this paired view. Strict FIFO — the IRS default for property, which tax tools
expect — is `snapshot({ linkage: false })` / `matchFifo(fills, { linkage: false })`; nothing in the live
path uses it, so use it for a tax-style reconciliation. The CSV export is the raw fill log and is
unaffected.

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

Every action lives in `src/core/commands.js` (34 commands). The Chrome message handler, the CLI and
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
export SMT_API_TOKEN="$(openssl rand -hex 24)"       # value is not printed
node tools/api-server.js --port 8787                # requires SMT_API_TOKEN
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

## SolTUI bridge and auto-reload

Everything the SolTUI app can do is also a SolTUI registry command (`soltui/commands.py`), and the
extension reaches that registry through a Chrome **native messaging** host, `com.mitchhudson.soltui`
(`soltui/native_host.py`). Two registry commands forward calls to it: `soltuiCommands` (list) and
`soltuiCall --command <name> --params '{...}'`. Both return **soltui's own envelope, unchanged**
(`{ok, command, result, error}`): the extension message, `node tools/cli.js` and the API return
exactly what `soltui call` prints. A missing, crashed or slow host is an ordinary `failed` or
`timeout` envelope with an install hint, never an exception. The extension adds no access rules of its
own: a command with `requires_confirm` needs `confirm: true` inside `params` on every surface, and soltui
refuses without it.

```bash
node tools/cli.js soltuiCommands --json
node tools/cli.js soltuiCall --command liquidity.status --json
curl -s -X POST -H "Authorization: Bearer $SMT_API_TOKEN" -H 'content-type: application/json' \
  -d '{"command":"liquidity.status","params":{}}' http://127.0.0.1:8787/v1/soltuiCall
```

- **Permission.** The manifest gains `nativeMessaging` and nothing else. Chrome only lets the origins in
  the host manifest's `allowed_origins` talk to the host. Install the host with
  `python -m soltui.native_host_install install`, then reload the extension once so the new permission
  takes effect.
- **Transports.** A dashboard renews a session through `soltuiSession`; the service worker retains one
  multiplexed `connectNative` port while dashboard leases or requests need it. Native replay/job state
  survives successive calls, and status/cancellation can answer during long commands. Without a dashboard,
  probes use a short-lived port. The CLI/API spawn the same host and speak the same 4-byte framing.
  Both feed `src/core/soltui.js`, which keeps envelopes unchanged. Quick calls get 30 s; long calls get
  15 min. A timed-out dashboard call is not retried and does not close other calls. Check status before
  continuing; a submit may have succeeded. `SOLTUI_NATIVE_HOST` or `SOLTUI_PYTHON` select node hosts.
- **No engine lock.** `soltuiCall` does not take the engine's store lock, so a long backtest never stalls a tick.
- **Dashboard.** The SolTUI panel (`src/ui/soltui-panel.js`) lists `soltuiCommands`, builds the form from
  each command's param types, gates `requires_confirm` behind a checkbox, sends only listed names, and
  renders untrusted values as text. Parameter edits and every attempt reset confirmation. Workspaces,
  tables, CSV, charts and the editor are described in [dashboard parity](../docs/EXTENSION-TUI-PARITY.md).
- **Wallet pubkey button.** Next to the dashboard's Wallet pubkey field, **Use soltui Solana address**
  (`src/ui/wallet-pubkey.js`) sends `soltuiCall` for the read-only soltui command `wallet.addresses`, which returns the
  public Solana and EVM addresses saved in soltui Settings and never an xpub or key material. The page checks the
  reply is a Solana public key (32 bytes of Base58), fills the field and says so; the owner still clicks Save. The
  page writes no `chrome.storage` itself.
- **Auto-reload on update.** A 1-minute `chrome.alarms` job asks the host for `buildHash`, a SHA-256 over
  `manifest.json` and everything under `src/` in the extension directory. When the hash differs from the
  one stored in `chrome.storage.local` (`soltuiBuild`) it calls `chrome.runtime.reload()`, under these rules
  (`src/core/autoreload.js`):
  the first observation only stores the hash; an unreachable host never reloads and is logged once until it
  recovers; a reload is **deferred, not forgotten,** while any tick, reconcile, submit or cancel is queued or
  running, or a dashboard session remains open (the engine lock and native session leases); the final check and the reload happen inside that
  lock, so a tick cannot start between "idle" and "reloaded". Each reload is one `auto-reload` event
  (hash prefixes, `armed`, `killSwitch`; no secret) in the existing event log.
  **A reload is an update, so it disarms**: `handleInstalled` forces `armed: false` on every update and keeps
  the kill switch and mode. After an auto-reload the operator re-arms deliberately.
  The hash covers the directory the host serves (`<repo>/extension`), which is the unpacked path Chrome Beta
  loads for this extension id.

---

## Layout

```
manifest.json              MV3 manifest: storage, alarms, nativeMessaging, notifications; Jupiter, Base/Solana RPC and DefiLlama hosts
src/core/grid.js           Pure grid engine — levels, side selection, planning, capital needs
src/core/risk.js           Risk rails and batch admission
src/core/pnl.js            FIFO matching, snapshots, equity curve, drawdown, CSV
src/core/engine.js         The tick: reconcile -> ingest fills -> plan -> admit -> place
src/core/commands.js       The command registry — every action, transport-agnostic
src/core/soltui.js         soltui bridge: envelope passthrough, timeouts, clean errors (transport injected)
src/core/autoreload.js     Auto-reload gate: first observation, idle check, host-down logging
src/core/alerts.js         Pure alert rules: modelled / backtest / quoted, merge, acks, notify filter
src/market/net.js          Read-only fetch + JSON-RPC (refuses any non-read method), endpoint fallback
src/market/evm.js          Hand-rolled ABI slice: selectors, words, int24, strings, exact unit conversion
src/market/tokens.js       Chains, endpoints, known Base and Solana tokens
src/market/holdings.js     Base and Solana balances in USD; partial failures named, never zeroed
src/market/pools.js        DefiLlama yields: normalise, rank by 30-day mean, 10-minute cache
src/market/quote.js        Swap quotes: Jupiter Metis; Slipstream on-chain CL math with range refusal
src/jupiter/http.js        Retry/backoff, Retry-After, request budget, per-attempt timeout
src/jupiter/price.js       Price API, tolerant of both response shapes
src/jupiter/trigger.js     Trigger V2: auth, vault, deposit craft, create, manage
src/venues/index.js        VenueAdapter contract, dry-run wrapper, read-only Perps
src/venues/triggerVenue.js The live-capable adapter
src/wallet/solana.js       base58, shortvec, signature insertion (no web3.js dependency)
src/wallet/signer.js       Null / pending-approval / session-key signers + encrypted vault
src/storage/store.js       IndexedDB journal + chrome.storage config
src/storage/fileStore.js   The same interfaces on JSON files, for the CLI and API
src/bg/service-worker.js   Alarm scheduling, message plumbing, badge, build-hash probe
src/bg/soltui-transport.js connectNative transport to the soltui host
src/ui/dashboard.*         Tabbed dashboard shell and router; views in src/ui/view-*.js, helpers in ui-kit.js
src/ui/popup.*             Holdings, alerts, shortcuts; grid controls collapsed under "Grid"
icons/                     Toolbar and notification icons (generated, no external asset)
tools/cli.js               CLI surface, generated from the registry
tools/api-server.js        Local HTTP API surface, generated from the registry
tools/soltui-transport.js  Node transport to the same soltui host (CLI and API)
tools/dryrun.js            Headless end-to-end tick
tools/e2e.mjs              Real-browser e2e (Chrome for Testing, DevTools pipe); helpers in e2e/
test/                      361 tests, no npm dependencies (node:test)
```

No build step and no npm dependencies. The one runtime library is Lightweight Charts 5.2.1, vendored
and pinned in `vendor/lightweight-charts/` (see its README; loaded lazily by `src/ui/charts.js`).
Plain ESM modules load directly as an unpacked extension —
`@solana/web3.js` would have added a megabyte to a service worker for base58 and one signature
insertion, so those are ~150 lines in `src/wallet/solana.js` instead, with tests against real mints.

---

## Verification status

**Redesign gate (2026-11-07, 0.3.0):** 351 tests pass; the oscillating dry run still nets +$0.3492;
`npm run e2e` passes 21/21 in Chrome for Testing, with the network audit widened to the read-only
market calls and every JSON-RPC body checked for read methods. A live, read-only run against the
owner's public addresses read Base $2.25 and Solana $51.33, quoted 0.01 ETH → 22.32 USDC through
Slipstream and 0.5 SOL → 44.75 USDC through Jupiter, refused a 5,000 WETH Base quote past the active
range, and listed 5,403 Base and Solana pools. No transaction was built or signed.

**Current offline gate (2026-11-07):** 303 tests pass. The deterministic oscillating
dry run closes one round trip: gross $0.3738, fees $0.0246, net +$0.3492, with no
unknown-fee fills. Public endpoint reachability passed; the keyed price check skipped.
Live money movement remains blocked without the transaction-intent verifier described
in `docs/jupiter-trigger-contract.md`. Unmatched sales, missing execution evidence and
unknown accounting costs hold new planning. The planner allows at most 10,000 rungs.

**Real-browser e2e (2026-11-07):** `npm run e2e` loads the unpacked extension into Chrome for
Testing (156.0.8078.47) and passes every check (20, or 21 with the production soltui host): the MV3 service worker starts, the extension
installs disarmed in dry-run, the popup and dashboard render, a dry-run `plan` is priced by a stubbed
read, a disarmed `tick` is skipped and journals nothing, the rails fail closed in the browser, a canary
API key appears in no DOM, response or `chrome.storage.sync`, and Chrome-level interception saw no request
other than the stubbed price read. It also drives the soltui bridge through the real extension and a real
native messaging host: `soltuiCommands` and a read-only `soltuiCall` return the same envelope as the
extension CLI and, with the production host, byte-identical to `soltui list` and `soltui call`; the
dashboard panel renders the result as text; a missing host is a clean `failed` envelope. This verifies
loading, dry-run behaviour and the read-only bridge only. It never arms or signs, it calls only commands
soltui lists as `read_only` (`e2e/lib/guard.mjs`), it does not exercise authenticated Jupiter responses,
and **no live order has ever been placed**. Not verified by any test: an actual `chrome.runtime.reload()`
in Chrome (the gate is unit-tested with a fake `reload`, because a reload would end the test session), and
the owner's own browser, which needs the one-time extension reload for the new `nativeMessaging`
permission.

**Historical development receipts (the figures below are not the current gate):**

- `npm test` → **110 passing, 0 failing** (unit, integration and three-surface parity)
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
   rewrite historical fill sizes. Quantity and execution value now require actual fill evidence;
   a planned intent does not prove either quantity or execution price.
5. **XSS-shaped table rendering** — journal rows interpolated venue-supplied order IDs and error
   strings into `innerHTML` behind a hand-rolled escaper, on a page holding extension privileges.
   Rows are now built with `createElement`/`textContent`.
6. **`window.prompt()` as the live-arm gate** — Chrome suppresses modal dialogs in an extension
   popup, so the confirmation would silently no-op or close the popup. Replaced with an inline
   typed confirmation.
7. **Cancelled orders booked as fills.** `getFills()` reads the orders/**history** endpoint, and
   history holds every *terminal* order — cancelled and expired as well as filled. There was no
   execution gate, so a cancelled order took its price from `triggerPriceUsd` and its quantity from
   the intent's **planned** size, then stored a fill for inventory the wallet never acquired and
   marked the intent `filled`. Reproduced end to end before fixing. `ingestFills` now requires
   positive evidence of both execution quantity and price, plus a real timestamp. Missing values
   hold planning. An explicit unexecuted cancellation can be ignored; other uncertain history
   remains visible for review.
8. **An unrecognised order envelope read as "no orders".** Covered under "Not verified" #2 below:
   an empty list is indistinguishable from a misread one to reconciliation, which treats it as
   "nothing is live" and re-plans every resting rung. Now refused.

**Measured on real SOL for the first time (2026-08-04).** The ladder economics were run
against the real daily and hourly series, not just synthetic bars —
`backtester/guides/ladder_grid.md` and `research/results/ladder_grid_sol.csv`.
Two results matter here:

- **A static ladder is out of range 86–93% of the time.** Using this extension's own
  `tools/dryrun.js` convention (0.85x–1.15x of price, 7 rungs, $12/rung), the ladder set
  once at the start of the daily series sat outside the market for 93.1% of bars. It still
  cut max drawdown from holding's **−96.27% to −11.46%**, which is the honest case for the
  strategy, but it earned +5.21% while holding earned +88.25%.
- **Re-centring in the simulator looked like the fix. The version that is safe to ship is
  not the version that was measured.** Reset the ladder from each block's opening price and
  the daily median becomes **+7.5% of deployed capital with 5 of 8 blocks positive**; the
  worst block still lost **22.5%**, consistent with the −$8.62 on $48 from the dry run.
  `planGrid` now has an opt-in `autoRecentre` (below) — but **that +7.5% does not transfer to
  it**, and the two must not be quoted together. The simulator moved the ladder
  unconditionally every block. `recentreDecision()` may only move it when nothing is resting
  and no lot is open, because `tick()` cannot cancel, so it fires far less often. Measured on
  the same daily series with `tools/measure-recentre.js`, it fires **once, on the first bar**,
  and then the ladder is frozen again for 1,874 bars.

**Not verified — do these before risking money:**

1. **No live order has been placed.** The bundled signer cannot verify the economic intent of
   a remote-crafted deposit/cancellation transaction. Live signing refuses before sending it to
   the raw signer. A trusted verifier must be implemented and tested before any funded live test;
   a key and funded wallet alone do not satisfy that requirement.
2. **Order-list response envelope — still unverified, but now loud.** The field names in
   `normaliseOrders()` have never been checked against a real response, and that has not changed.
   What changed is the failure mode. It used to return `[]` for a shape it did not recognise, and
   reconciliation reads an empty list as "nothing is live" — so every resting rung looks orphaned
   and gets re-planned, which is the double-fire path. It now throws `OrderEnvelopeError`, and
   because `tick()` wraps its whole body, an unreadable envelope aborts the tick before anything is
   placed. An order missing a field reconciliation needs (`venueOrderId`, `side`,
   `triggerPriceUsd`) is refused by name rather than passed along unmatchable.

   So this item is *safer*, not *closed*: the mapping still needs checking against a live response.
   Use `normaliseOrders(body, { strict: false })` to inspect one by hand — it flags unusable orders
   instead of throwing. Accepted envelopes are `ORDER_LIST_KEYS`; required fields are
   `ORDER_REQUIRED_FIELDS`. Both are exported so correcting them is a one-line, visible diff.

   `getOpenOrders()` refuses unusable configured-pair records. `getFills()` preserves flagged
   records for inspection, but the engine holds planning when execution evidence is incomplete:
   skipped history could otherwise hide inventory or daily loss. Two candidate list keys holding arrays (`{orders: [], data: [...]}`)
   is treated as ambiguous and refused: taking the first would reintroduce the empty-list bug through
   a second door. A trigger price must be positive, not merely present, since `Number('')` is `0`.
3. **Fee attribution — where Trigger reports fees is still unconfirmed.** Fees are no longer
   coerced to zero when absent. `normaliseOrders()` leaves `feeUsd` as `null` and sets
   `feeUnknown`; `ingestFills()` still records the fill (dropping a real fill would lose inventory
   the wallet holds) but flags it and counts it on `result.feeUnknownFills`. A non-zero count means
   the reported P&L understates costs by however much those fees were. The count reaches humans in
   three places: `summarise()` puts it in the event log, the popup appends `?` to the fee total, and
   the dashboard renders `$0.00?` on any fill whose fee the venue never reported. A safeguard nobody
   can see is not a safeguard.
4. **Chrome alarm floor.** 30s is assumed; the engine logs the real wake delta. Watch it before
   trusting a sub-minute tick.
5. **Transaction signature insertion** is tested against synthetic transactions, not a real
   Jupiter deposit transaction.

**Deliberately stubbed, each throwing a message that says how to finish it:**

- `PerpsVenueReadOnly` — all methods throw `NotImplemented` with the concrete next step
  (decode position accounts via `getProgramAccounts` + the perps IDL)
- Jupiter Lend borrow as a margin source — `leverageFeasibility()` refuses and explains
- `PendingApprovalSigner` queues transactions but the dashboard has no approval UI yet, so
  the pending-approval primitive cannot complete an order; Trigger also requires its trusted verifier
- OCO/OTOCO bracket bodies exist in the client but the grid only emits `single` orders

---

## Legal and operational notes

- This integrates via Jupiter's **documented public APIs**, not by automating the jup.ag UI.
  Scraping or driving the frontend would be brittle and a worse ToS position. Review the
  [Jupiter SDK/API License Agreement](https://developers.jup.ag/docs/legal/sdk-api-license-agreement)
  before running this against real funds.
- **Three licence obligations this extension does not yet meet.** The agreement was read on
  2026-08-04 (see `../docs/trading-signals-concept-family.md` §6.1 for the full reading; **not legal
  advice**). It contains no clause against bots or automated trading, but it does require:
  §8.4 — the product must **prominently display "Powered by Jupiter"** to end users; §2.3 — it must
  prominently label *which* routing API is used ("Jupiter Ultra" vs "Metis"), and presenting output
  as merely "Jupiter" is explicitly called out; §6.1 and §13.1 — use is **fee-bearing with a 30-day
  minimum term paid in advance**, which sits awkwardly beside the portal's $0 "Free" tier. Liability
  is capped at **USD 100** (§10) under **Panama law** (§14).
- **§3.2(g) forbids combining API content with scraped content.** This repository contains both a
  scraped `../jup.ag/` mirror and `../pagesource` alongside this API client. Reading them to
  *understand* the platform is a different act from feeding them into the running product beside API
  responses. Keep that boundary explicit — nothing in `src/` reads either artifact today, and it
  should stay that way.
- Trigger V2 requires an API key for every call, and rate limits apply per tier. The client
  implements backoff and a request budget, but a tight tick across many rungs will still find the
  ceiling.
- Automated trading may have tax and reporting consequences. Every fill is a disposal; the CSV
  export exists for that reason.
- Minimum order size is **$10**, so a 7-rung grid needs meaningful capital before it is even legal
  on the venue. The dashboard computes the requirement for your configuration.

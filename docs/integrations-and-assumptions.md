# Integrations and assumptions

External services this repo depends on, and the assumptions baked into the code that would
be wrong somewhere else. The second list is the one that bites.

## External services

| Service | Used by | For | If it changes |
| --- | --- | --- | --- |
| Coinbase Exchange (`api.exchange.coinbase.com`) | `backtester/core/fetch.py`, `fetch_minutes.py`, `ticks.py`, `universe.py` | OHLCV, trade ticks, listed products | Revalidate refreshed caches; cached simulations remain offline |
| Hyperliquid / OKX | `backtester/core/funding.py` | Historical signed funding, with OKX as a shallow cross-check | Carry research must retain venue, interval and coverage limits |
| Base RPC, Aero / Multicall3 contracts | `liquidity/src/aero_lp/chain.py`, `executor.py` | On-chain reads, exact simulation, optional signed transactions | Wrong chain/stale head must fail closed; ambiguous sends need reconciliation |
| GeckoTerminal | `liquidity/src/aero_lp/market.py` | Prices, pool discovery and hourly closes | Missing or rate-limited data can prevent scoring |
| DefiLlama | `liquidity/src/aero_lp/providers.py` | Comparison-only yield/price inputs | Quoted rows are labelled; no non-Aero deployment is authorized |
| MongoDB | `mongo/schema.py`, `mongo/load.py` | Derived research records | Rebuild selected collections from tracked evidence and local caches |
| Jupiter Price v3 (`api.jup.ag`, `lite-api.jup.ag`) | `extension/src/jupiter/price.js`, `backtester/core/archive_price.py` | Live and snapshot prices | The extension cannot price a tick; it refuses rather than guessing |
| Jupiter Trigger v2 (`api.jup.ag/trigger/v2`) | `extension/src/jupiter/trigger.js` | Live-capable price-order adapter, currently blocked without a trusted transaction-intent verifier | Public-contract offline fixtures do not establish authenticated wallet responses, actual costs or live acceptance |
| Oracle reference feeds | `oracle/feeds.py` `RecorderFeed`, `JupiterPriceFeed` | Exact-instrument local recorder reads or explicit Jupiter Price v3 GETs; no signing or order submission | Jupiter requires `JUPITER_API_KEY`, defaults to 5s with a 15s cap, bounds replies, refuses redirects and does not retry in the transport; missing/stale inputs remain unavailable |
| Oracle stdio MCP | `oracle/server.py` | Eight read-only tools and three subscribable archive resources | Same-user local process/filesystem boundary, no network listener or remote auth; subscriptions invalidate snapshots rather than delivering every tick; standalone selected archive startup may initialize its schema |
| Official Coinbase CLI | `oracle/coinbase_orders.py`, `oracle/webhook_orders.py` | Separately enabled TradingView worker's account/product/order reads and one committed spot-order create | Existing CLI authentication and exact portfolio binding; default 30s subprocess deadline, bounded captured output, fixed errors and no automatic submit retry; ambiguous outcomes retain journal holds |
| GUM Beta (`api.gum.ag/perps`) | `oracle/gum_orders.py`, `oracle/gum_webhook_orders.py` | Owner-scoped health/market/account/history GETs and separately enabled signed ZEC order-Action POST | `X-PUBKEY` owner selection for reads; local owner-bound signature for writes, 15s transport deadline, 2MiB reply cap, no redirects or automatic POST retry; funding/deposits remain separate from order verification |
| Chrome extension APIs (MV3) | `extension/src/bg/`, `src/storage/` | Service worker, alarms, `chrome.storage`, IndexedDB | MV3 timer and lifetime rules are load-bearing, not incidental |
| launchd (macOS) | `soltui/soltui-service`, `liquidity/scripts/aero-lp-service` | Optional login services | `KeepAlive` overriding Quit is a launchd property, not a bug in the app |
| Solana RPC, Jupiter Swap/Price and LI.FI | `executor/src/executor/rpc.py`, `jupiter.py`, `lifi.py` | Guarded spot quote/build/simulation/send; LI.FI is quote-only | Reads and sends have different retry semantics; unknown sends block new execution |
| Cloudflare Workers, static assets and D1 | `website/src/worker.js`, `website/wrangler.jsonc` | Hosted wallet accounts, sessions and inactive paper definitions | Preserve tenant scope and single-use challenges; website definitions do not trade |
| Stripe (`api.stripe.com`) | `website/src/worker.js` | Subscription Checkout, portal and verified entitlement | Signed webhook plus canonical subscription state, never a redirect, gates access |
| Separate HTTPS analysis adapter | `website/engine/server.py`, Worker `engine` helper | Canonical backtests and read-only Oracle archive views | Missing cache, archive or credentials stays unavailable; no tunnel to local trading services |
| Coinbase public WebSocket and dedicated MongoDB time series | `scripts/capture_market.py` | Bounded raw-event spool and independent upload | Preserve the persisted deadline and ambiguous-insert marker; never let the derived loader drop this namespace |

Full per-call detail — timeouts, retries, what is logged — is in `docs/external-calls.md`.

## Assumptions in the code

### A year is 365 days, not 252

Crypto trades every calendar day. `HOURS_PER_YEAR = 365 * 24` and `periods_per_year()` in
`backtester/core/types.py` follow from that, and the choice is stated in the report output
rather than buried. Any figure compared against an equities benchmark that annualises on
252 trading days is not comparable.

### Borrow rates are basis points per hour

`CostConfig` expresses them that way deliberately, to sidestep a documented deci-bps
ambiguity in the venue's own documentation. 1.6 bps/hr is 0.016%/hr, roughly 140% APR,
which is the documented SOL reference point.

The default `min_hourly_rate_bps = 0.0` preserves the *published* flat-linear formula.
Governance proposed a dual-slope model with a rate floor that is incompatible with it; set
that field to model the proposal instead.

### `max_lev_constant = 500` is a protocol constant

Distinct from the user-facing leverage cap. It gives a maintenance margin fraction of
0.002. Do not conflate the two.

### Fills happen at the next bar's open

`fill_delay` defaults to 1: a decision at bar `t` fills at the open of `t+1`. Setting it to
0 means close-to-close fills, which is optimistic. Anything reading a target exposure as
"the position held now" has to account for the delay — under the default, the exposure held
at the last bar is the target decided one bar earlier.

### A liquidation that gapped through the level fills near the open

SOL has gapped more than 20% in a day. Assuming the better price would flatter every
leveraged result, so when the bar gapped through the liquidation level the fill is taken at
roughly the open rather than at a level that never traded.

### Equity is floored at zero

Margin is isolated per position, so a trader cannot lose more than the collateral posted.
Negative equity is unphysical here and would poison CAGR and drawdown with a sign flip.

### Binance is unavailable from here

Geo-blocked, which is why Coinbase is the fetch source. Coinbase's candle endpoint returns
rows in a non-OHLCV order that has to be handled on the way in — remember this if you add
a source or change the fetch path.

### The venue's order list is the truth, local state is a cache

Asserted at the top of every extension tick. The corollary is the important half: an intent
that was submitted but is not live becomes `unknown` and is **never** auto-retried, because
auto-retry is exactly how a rung double-fires after a crash.

### `chrome.storage.sync` never holds secret material

The API key and the session-key vault are `chrome.storage.local` or a mode-0600 file only.
`setApiKey` returns a length, never the key.

### soltui's bundle path is absolute

The py2app alias build references this checkout, so moving the repo breaks the installed
app until `soltui-service build` is rerun. A full freeze would have to embed pandas and
numpy.

## Environment differences

| | Development here | CI | Someone else's machine |
| --- | --- | --- | --- |
| OS | macOS (Darwin) | Ubuntu jobs plus a macOS soltui job; MongoDB job pins Ubuntu 22.04 | Core CLI tools are portable; menu-bar/launchd integration needs macOS |
| Python | 3.13 | 3.13, pinned | Must be 3.13 |
| Node | 22 (`.nvmrc`) | 22, pinned | Must be 22+ for WebCrypto Ed25519 |
| `data/` | Populated by hand | Absent — gitignored | Absent; refetch required |
| Jupiter reachability | Available | Only on `workflow_dispatch`, `continue-on-error` | Needs a key for the non-`lite` host |
| Chrome | Separate installed profile acceptance | Chrome for Testing in temporary profiles, network-stubbed extension checks and isolated native paper-owner recovery | Needed for the extension; everyday-profile installation remains a separate gate |

Offline unit suites must not require public network access or pre-existing cached CSVs.
MongoDB integration tests use a service container in CI and skip locally if no server is
available. Soltui runs on a macOS CI runner; its private supervisor dependency is excluded
there, so dependent checks can skip. Liquidity network tests are a separate explicit gate.
The installed app bundle and live services still need manual acceptance beyond CI.

## What would need changing to run this elsewhere

1. **A different data vendor.** `fetch.py` is Coinbase-shaped, including its row ordering.
2. **A different venue.** `src/venues/` is the seam — `triggerVenue.js` is one
   implementation. `docs/known-issues.md` retains the difference between offline public-contract
   fixtures and unresolved authenticated wallet, cost and live-execution acceptance.
3. **Non-macOS soltui.** The menu-bar app, py2app and launchd are all macOS-specific. The
   TUI (`tui.py`) is not.

# Integrations and assumptions

External services this repo depends on, and the assumptions baked into the code that would
be wrong somewhere else. The second list is the one that bites.

## External services

| Service | Used by | For | If it changes |
| --- | --- | --- | --- |
| Coinbase Exchange (`api.exchange.coinbase.com`) | `backtester/core/fetch.py` | All OHLCV history | Every backtest moves. There is no second source |
| Jupiter Price v3 (`api.jup.ag`, `lite-api.jup.ag`) | `extension/src/jupiter/price.js`, `backtester/core/archive_price.py` | Live and snapshot prices | The extension cannot price a tick; it refuses rather than guessing |
| Jupiter Trigger v2 (`api.jup.ag/trigger/v2`) | `extension/src/jupiter/trigger.js` | Placing, listing, cancelling real orders | The money path. Reconciliation depends on its response shape, which is **guessed** |
| Chrome extension APIs (MV3) | `extension/src/bg/`, `src/storage/` | Service worker, alarms, `chrome.storage`, IndexedDB | MV3 timer and lifetime rules are load-bearing, not incidental |
| launchd (macOS) | `soltui/soltui-service` | Supervising the menu-bar app at login | `KeepAlive` overriding Quit is a launchd property, not a bug in the app |

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
| OS | macOS (Darwin) | `ubuntu-latest` | Anything, except `soltui/` needs macOS |
| Python | 3.13 | 3.13, pinned | Must be 3.13 |
| Node | 22 (`.nvmrc`) | 22, pinned | Must be 22+ for WebCrypto Ed25519 |
| `data/` | Populated by hand | Absent — gitignored | Absent; refetch required |
| Jupiter reachability | Available | Only on `workflow_dispatch`, `continue-on-error` | Needs a key for the non-`lite` host |
| Chrome | Present, extension loadable | None — never loaded in CI | Needed for the extension |

Two consequences worth stating: **no test may require the network or a cached CSV**, since
CI has neither; and **`soltui/` cannot be tested on the Linux runner**, so its 95 tests are
a local gate rather than a CI one.

## What would need changing to run this elsewhere

1. **A different data vendor.** `fetch.py` is Coinbase-shaped, including its row ordering.
2. **A different venue.** `src/venues/` is the seam — `triggerVenue.js` is one
   implementation — but `docs/known-issues.md` applies: the Trigger envelope is guessed, so
   a second venue is also a chance to find out what the first one really returns.
3. **Non-macOS soltui.** The menu-bar app, py2app and launchd are all macOS-specific. The
   TUI (`tui.py`) is not.

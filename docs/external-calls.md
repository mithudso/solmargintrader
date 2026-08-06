# External calls

Every call in this repo that leaves the machine. Four of them, across two components;
`research/` and `soltui/` make none.

The engine and the readout never touch the network — that is a stated invariant, not an
accident. Fetching is always a separate explicit step that writes a local cache, so a
simulation cannot silently depend on a live endpoint.

## Inventory

| # | Call site | Target | Transport | Timeout | Retry | Logged? | Tested? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `backtester/core/fetch.py:56` | `https://api.exchange.coinbase.com` | `urllib.request.urlopen` | 20s | Paged loop, no backoff | stdout progress | Yes, against a fake |
| 2 | `backtester/core/archive_price.py:62` | `https://lite-api.jup.ag/price/v3` | `urllib.request.urlopen` | Parameter | None | stdout | Yes |
| 3 | `extension/src/jupiter/price.js` → `src/jupiter/http.js` | `https://api.jup.ag/price/v3` (`lite-api` without a key) | `fetch` | 15s per attempt | 4 attempts, full-jitter backoff, budgeted | **No** | Yes, against a fake |
| 4 | `extension/src/jupiter/trigger.js` → `src/jupiter/http.js` | `https://api.jup.ag/trigger/v2` | `fetch` | 15s per attempt | 4 attempts, full-jitter backoff, budgeted | **No** | Yes, against a fake |

`extension/tools/verify-endpoints.js` also reaches Jupiter, but as a deliberate manual
reachability probe rather than a code path an order depends on. CI runs it only on
`workflow_dispatch`, so a third-party outage cannot turn every PR red.

## Per-call notes

### 1. Coinbase OHLCV — `backtester/core/fetch.py`

The only market-data source for the backtester. Binance is geo-blocked from here, which is
why Coinbase is the default and why its non-OHLCV row ordering has to be handled on the
way in. Writes a validated CSV into `data/`; the engine reads only that cache.

### 2. Jupiter spot price — `backtester/core/archive_price.py`

Snapshots a single mint's USD price. `data/JLP_spot.csv` is the output: one row, with
columns `timestamp,iso,mint,usd_price,source` — **not** OHLCV. Anything expecting bars
must reject it, and `research/decide.py` does, naming the missing columns.

### 3–4. Jupiter price and Trigger — `extension/src/jupiter/`

Both go through `src/jupiter/http.js`, the single HTTP layer. This is the money path: the
Trigger API is what places, lists and cancels real orders.

That layer is the most carefully built of the four. It retries up to 4 attempts with
full-jitter exponential backoff (`backoffDelayMs`, base 500ms, cap 15s) — jittered because
several rungs retrying in lockstep would re-collide — and charges a token-bucket request
budget **per attempt** rather than per call, so a retry storm cannot bypass the budget. The
per-attempt timeout is `DEFAULT_TIMEOUT_MS` (15s). Without an API key it falls back to the
`lite-api` host.

Two cautions carried from `extension/README.md`:

- **No live order has ever been placed** through this code.
- The Trigger **order-list response envelope is guessed.** Reconciliation reads it at the
  top of every tick and treats the venue as the source of truth, so if the real envelope
  differs, reconciliation is wrong in the most consequential place there is.

Neither call logs its request or outcome. See `docs/logging.md` — that is gap 1 there, and
it is the reason a wrong envelope would be hard to diagnose.

## The five standards

The mdb-tam standard asks each external call to carry a CLI trigger, a centralized error
log, an auto-remediation map, a dashboard card, and datastore verification. This repo has
no server, no operations registry and no remediation engine, so most of that machinery
does not exist here and inventing it would be worse than not having it. Current state,
stated plainly:

| Standard | Status |
| --- | --- |
| CLI trigger | **Met.** Every call is reachable from a CLI: `backtester.core.fetch`, `backtester.core.archive_price`, `tools/cli.js`, `tools/verify-endpoints.js` |
| Centralized error log | **Partly.** The extension has a persistent events store but neither Jupiter call writes to it (`docs/logging.md`, gap 1) |
| Auto-remediation map | **Not applicable.** No remediation engine in this repo. A failed fetch is re-run by hand; an order that did not appear live becomes `unknown` and is deliberately **never** auto-retried |
| Dashboard card | **Partly.** `src/ui/dashboard.js` shows tick state and recent events, not per-call health |
| Datastore verification | **Met for fetch.** `core/data.py` validates every cached CSV — schema, ordering, gaps — and checksums it, and the readout prints that checksum |

The honest summary: calls 1 and 2 are adequately covered for a component that cannot lose
money. Calls 3 and 4 need the logging in `docs/logging.md`'s gap list before the live path
is exercised for real.

## Adding a call

1. Route it through the component's existing layer — `src/jupiter/http.js`, or `urlopen`
   with an explicit timeout. Do not add an HTTP client dependency.
2. Give it a timeout. Every call above has one.
3. Log the request and the outcome to the events store (extension) or stdout (Python).
4. Test it against a fake, never the live endpoint — CI must stay green through an outage.
5. Add a row to the table above. `scripts/check_docs.py` does not yet diff this inventory
   against the source, so this step is on the author.

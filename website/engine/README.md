# Public-analysis bridge

This service exposes the canonical Python exposure-strategy backtester and inert
Oracle archive reader. It cannot sign, submit orders, read account portfolios or
control the owner's local services. The website Worker keeps its bearer token
server-side. Do not give a browser this token.

Run from the repository root with Python 3.13 and the existing backtester/Oracle
dependencies installed. `ENGINE_TOKEN` must contain at least 32 random characters.
Set `ENGINE_DATA_DIR` to a dedicated public-analysis OHLCV directory. Its filenames
are `SOL_1h.csv`, `BTC_1d.csv`, and analogous allow-listed coin/interval names. CSV
schema is `timestamp,open,high,low,close,volume`. The source label and USD quote
are operator assertions; this adapter does not certify them. Set
`ENGINE_ORACLE_DIR` to a separate directory with `SOL/history.sqlite3`,
`BTC/history.sqlite3` and other approved archives. Set `ENGINE_ORACLE_QUOTE` to
`USD`, `USDC` or `USDT` to bind the exact archive instrument. Never substitute a
stablecoin quote without naming it.

The default listener is loopback. For an external deployment, use the included
Dockerfile with repository-root build context, read-only dedicated input mounts,
and an HTTPS gateway or private Cloudflare Tunnel. Set the Worker's `ENGINE_URL`
to the HTTPS origin and `ENGINE_TOKEN` to the same secret. Do not tunnel the local
control room. The container requires no signing keys or trading credentials.

`python -m website.engine.server` starts only this analysis listener. It does not
start a feed, recorder, inference service, strategy worker or history acquisition.
`python -m unittest website.engine.test_server website.engine.test_research -v`
runs fixture-only tests. The Dockerfile is provided for provisioning; a successful
source test does not establish that a container or remote service is deployed.

## Contracts and bounds

- `GET /v1/strategies` returns the complete canonical exposure-strategy registry.
  Other local ladder, pair, stop-order and event-replay runners are separate; this
  endpoint makes that scope explicit.
- `GET /v1/oracle?coin=SOL` reads only the matching archive. It ranks strategies
  admitted by the canonical current voting policy, by directional accuracy, then
  sample size, then stable ID. Stale market data, expired forecasts, insufficient
  evidence and mismatched policy identity produce no leading strategy. An
  unavailable leader is a truthful state, not an error to fill with an example.
- `POST /v1/backtests` accepts only `coin`, `strategy`, `interval`, `capital` and
  `leverage`. Four coins, six canonical intervals, leverage 1–10 and capital
  $1–$1,000,000 are allowed. One calculation runs at a time. The server accepts at
  most 4 KB JSON, reads a cache of at most 32 MB, and simulates its latest 6,000
  complete contiguous bars. Missing histories, gaps and unusable strategies fail
  closed. A response includes all engine metrics, gross metrics, exact default
  cost assumptions, full source hash, selected-bar hash and a downsampled chart.
  These default costs are a stated simulation model, not the user's fee tier or
  a venue quote. Perp simulation does not establish that a venue supports a coin.

The browser cannot call the bridge directly: requests with an `Origin` header are
refused. A bearer token is mandatory even for reads. All errors exposed by the
HTTP handler are symbolic and contain no local paths or raw exception messages.
The single worker slot bounds active calculations; production provisioning must
also set CPU/memory/request-rate limits and align edge request timeouts with the
chosen compute tier. This synchronous adapter is a bounded research path, not a
durable job scheduler or unattended trading service.

## Dedicated hosted runtime

The Container starts `python -I -m website.engine.runtime`; the standalone
read-only listener above remains available for compatibility. The dedicated
runtime explicitly acquires public Coinbase Exchange USD candles, maintains
separate native SOL/BTC/ETH/ZEC Oracle archives, and runs durable pure-analysis
jobs. It needs its own state root, owner epoch and authenticated R2 checkpoint
bridge. It never reads the owner's cached files, keys or control room.

Cold start restores and validates state before writers or jobs become ready.
Native SQLite backups, input data and job results use hash-checked R2 chunks
and an epoch/sequence-fenced manifest. The published manifest commits a state;
ephemeral container disk and a shutdown handler do not establish durability.
Dependencies are pinned in `constraints.txt`, and the image installs this
package before isolated-mode startup.

Historical1m closes initialize feature context only after their candles are
closed. They retain their actual candle bucket-start index and the explicit
`closed_candle_start_index` timestamp label, with actual current receipt time.
They are derived reference samples, not instantaneous trades or execution quotes.
The latest closed index is at least60seconds old, beyond the native15second
freshness gate, so this step creates **zero historical forecasts or resolutions**.
The CSV hash and sample semantics are recorded. Forecasts and measured accuracy
begin with genuine current provider events; missing buckets reset native warmup
and are never forward-filled. Qualification requires real prospective outcomes;
no leader or accuracy is invented during warmup.

`GET /health`, `POST /v1/jobs` and `GET /v1/jobs/{id}` supplement the unchanged
three analysis endpoints. New jobs pin their exact provider CSV and acquisition
metadata. One spawned child calculation runs at a time, with a45second deadline;
the legacy synchronous path uses the same durable executor with a15second
calculation deadline. Results are published only after durable checkpointing.
Source schema, deployment gates and tests are in `website/runtime/README.md`.

For a structurally valid job ID and canonical request, unsupported strategies,
invalid semantic parameters, queue-capacity refusal and input/history failures
produce a durable terminal `failed` receipt. The exact ID and request hash are
retained before returning HTTP200. Replaying the same ID cannot turn that
refusal into a new accepted job when a cache or strategy later becomes available.
The edge releases its own reserved credit only after verifying that terminal
receipt. Malformed JSON, malformed envelopes/IDs and idempotency conflicts still
reject without creating another accepted receipt. A failed checkpoint returns
an unavailable response rather than publishing uncommitted terminal state.

## Trusted strategy targets

The dedicated runtime adds `POST /v1/signals` with the exact JSON keys `coin`,
`strategy`, and `interval`. It computes the canonical default strategy in spot
mode over the latest fully closed contiguous public Coinbase USD bars, up to
6,000. Stateful callbacks receive the same guarded `BarWindow` and spot target
normalization as the canonical engine. The last closed-bar target applies to the
next bar (`fillDelay:1`); its historical close is never an execution quote.

An available response has `desiredExposure` exactly `0` or `1`, a stable
`signalId`, full selected-bar `inputHash`, raw-cache `sourceHash`, loaded
`sourceIdentity`, `strategyRevision`, `economicVersion`, `barStart`, `barEnd`,
`asOf`, `expiresAt`, and `executionQuote:false`. `marketObservation` includes
actual provider event and receipt times and identity, without a price. The ID
binds the market, strategy, interval, completed bar, selected inputs and strategy
revision. Changing an excluded partial candle cannot change that ID. The
revision binds the loaded source hash, strategy class/default parameters and
spot/fill-delay semantics. Each `GET /v1/strategies` row exposes the identical
`strategyRevision` for wallet-signed preauthorization.

Missing/stale selected history can trigger one bounded explicit public refresh
and a durable checkpoint before calculation. Canonical strategy calculation
never fetches data. A separate genuine current venue observation must be at most
15 seconds old; historical feature bootstrap cannot satisfy it. Signals expire
no later than that observation or the next bar end. Fractions, non-finite
targets, gaps, stale/missing observations, unusable strategies and a five-second
callback-loop compute budget produce explicit unavailable reasons. One shared
compute slot bounds signals and backtests; a busy runtime returns unavailable.
The authenticated trading driver must independently obtain a fresh execution
quote and enforce the customer's signed wallet policy. This endpoint supplies
no account, wallet, permission, order, execution price or signing capability.

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

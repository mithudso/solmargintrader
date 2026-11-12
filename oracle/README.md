# Oracle 0.2.3

Oracle is a local shadow signal service, defaulting to SOL/USDC. Explicit
`--instrument BTC/USD` (or another supported symbol/quote) binds each archive,
CLI and MCP process to that instrument. No quote conversion is implied. A single foreground daemon
consumes source-labelled observations into a durable historical SQLite archive.
It evaluates 14 existing strategy cards prospectively and serves snapshots,
history, guide routes, readiness and resource subscriptions through MCP.
The forecast service never loads signing keys or submits orders. Its research
readiness and veto remain advisory. A separately enabled TradingView webhook
worker can submit Coinbase spot orders through the authenticated official CLI,
or explicitly configured ZEC Beta perpetual orders through GUM on Jupiter.

## Install

Python 3.13 or newer is required. Install the canonical backtester and Oracle
in their own environment. Bot Manager is an optional read-only integration.

```sh
uv venv .venv --python 3.13                 # first setup only; reuse an existing .venv
uv pip install --python .venv/bin/python -e ./backtester -e ./oracle
.venv/bin/soloracle --help
```

Run these commands from the source repository root. Known missing Python
dependencies exit with code 3 and an isolated-environment repair command. Both
CLIs show usage on invalid arguments without echoing their values. MCP help
remains available before installing the optional protocol SDK. Install Bot
Manager separately only when using its optional read-only integration.

The package pins the official MCP Python SDK to 1.30.0. The backtester supplies
NumPy, Pandas, strategy code and packaged cards. No extension or Bot Manager
settings change on installation. No persistent service starts on installation.

## Market data and running

By default the daemon reads the existing SolTUI recorder's `latest.json` under
`~/.config/soltui/prices` (or `SOLTUI_CONFIG_DIR/prices`). It requires an actual
`SOL-USDC` entry. The recorder commonly contains `SOL-USD`; that is refused as
`instrument_unavailable`. Oracle does not start or reconfigure the recorder.

```sh
/Users/mitch/.venvs/soloracle/bin/soloracle run --source recorder
```

Jupiter's documented Price V3 endpoint returns token USD reference prices over
HTTP. Its SOL USD / USDC USD ratio is labelled `polled_reference_ratio`. It is
neither a push stream nor a tradable SOL/USDC quote. Set `JUPITER_API_KEY` through
your private process environment, then explicitly choose this source:

```sh
/Users/mitch/.venvs/soloracle/bin/soloracle run --source jupiter --interval 2
```

Credentials are not CLI arguments, archived values, or response fields. Missing
credentials, invalid prices, omitted mints, stalled/regressing block IDs and
network errors produce symbolic unavailable reasons. Initial upstream event age
cannot be certified from Price V3's block ID alone. Receipt freshness and unknown
upstream time remain separate; all reference predictions have `tradable=false`.
No verified Jupiter push feed is implemented. A future adapter must independently
establish source identity, ordering, event time and freshness before integration.

The default archive is
`~/.local/share/solmargintrader/oracle/history.sqlite3`. `--archive` precedes the
command. One owner lock fences each archive. A changed source or strategy/policy
version requires a new archive; this prevents accidentally pooling evidence.
The daemon runs until SIGINT/SIGTERM, retries feed failures with bounded backoff,
and stops on archive errors. Supervise this foreground command with the host's
service manager if unattended collection is required. `--max-ticks 1` is a bounded
read-only feed smoke. Do not put credentials into a committed service definition.

```sh
/Users/mitch/.venvs/soloracle/bin/soloracle status
/Users/mitch/.venvs/soloracle/bin/soloracle market
/Users/mitch/.venvs/soloracle/bin/soloracle predictions
/Users/mitch/.venvs/soloracle/bin/soloracle history --limit 100 --after 0
/Users/mitch/.venvs/soloracle/bin/soloracle strategies
/Users/mitch/.venvs/soloracle/bin/soloracle guidance --stage forward --repo /Users/mitch/dev/solmargintrader
/Users/mitch/.venvs/soloracle/bin/soloracle readiness --manager-home /Users/mitch/.config/solbot
/Users/mitch/.venvs/soloracle/bin/soloracle veto
```

## Strategies, evidence and votes

The selected existing cards are MA crossover, RSI, breakout, MACD, Bollinger
reversion, Bollinger breakout, Keltner, time-series momentum, stochastic, z-score,
SMA regime, EMA crossover, PPO and MA ribbon. `strategies` returns exact IDs,
parameters, warm-up, source/card hashes and version identities. The MA crossover uses the card-supported `short_when_below=true` variant so
falling trends can produce a bearish hypothesis. Its override and rationale are
versioned in the catalog; the other 13 cards retain their defaults. Exposure sign
is used as a directional hypothesis; flat exposure means FLAT, not DOWN. These are
not claims that all cards predict profit on Jupiter.

The service groups observations into completed 60-second sampled OHLC bins.
Missing bins reset warm-up. It does not invent trade volume: selected rules do
not read volume. Forecasts use only completed bins preceding issuance, reference
the issuance observation, and target 60 seconds later. They enter the archive
before later observations can resolve them. Each target needs an observation
within a 15-second tolerance; gaps are recorded without a hit or miss. A zero
price move resolves FLAT. All scored flat forecasts count in the denominator.
Shadow reference accuracy excludes fees, slippage, borrow, fills and P&L; use the
Backtester and paper execution evidence for economic qualification.

Evidence is cumulative within one source/instrument/policy/horizon/version.
Twenty resolved calls are required by default. A strategy votes only when its
resolved directional accuracy is strictly greater than 50%; exactly 50% is
excluded while shadow predictions continue. Weight is hits/resolved. More than
100 hits doubles that weight, so a perfect 101/101 record carries 200% of one
vote. Exactly 100 hits does not double. This is the documented provisional
interpretation of the owner's bonus rule.

Each completed-bar evaluation appends one `graphdb_ticks` row and fourteen
`graphdb_predictions` rows to the same archive transaction as the forecasts.
Rows retain the strategy direction (including warm-up/no-call), version, then
known hit/resolution counts, voting eligibility and weight, full-catalog
aggregate, observed price and compact shape metrics from preceding completed
bars. The `/api/oracle` response exposes the latest 240 graph ticks. The
control-room Oracle page uses the vendored TradingView Lightweight Charts
library to show observed prices with toggleable strategy and aggregate
direction markers. A marker is a direction at an observed price, not a price
target. Existing v1 archives remain readable and report graph history as
unavailable until a v2 evaluator records new ticks.

Flat votes contribute to total weight. Signed balance is 100 times the weighted
sum of directions divided by total weight. Balance >=60 is Strong Buy; >=20 is
Buy; <=-60 is Strong Sell; <=-20 is Sell; otherwise Flat. These are configurable
in code only with a new reviewed version, not measured optimum thresholds.
No eligible or current votes means unavailable. Stale market observations also
make aggregation unavailable. Neither balance nor historical accuracy is a
calibrated profit probability. The service does not tune or adopt parameters;
underperforming cards should receive a separately versioned shadow challenger
with prospective comparable outcomes before any promotion.

## MCP contract and subscriptions

```sh
/Users/mitch/.venvs/soloracle/bin/soloracle-mcp --archive /Users/mitch/.local/share/solmargintrader/oracle/history.sqlite3 --repo /Users/mitch/dev/solmargintrader
```

Configure that absolute executable as a local stdio MCP server. The daemon and
MCP readers use the same archive. Each client has its own process/subscriptions;
filesystem and process-owner access provide the local boundary. There is no
network listener, remote authentication or order capability.

Tools: `oracle_status`, `oracle_market`, `oracle_predictions`, `oracle_strategies`,
`oracle_history`, `oracle_guidance`, `oracle_readiness`, `oracle_veto`.
Tool arguments reject unknown fields; history pagination is bounded to 1,000.
The version-1 envelope has `schema_version`, `ok`, `data`, `error`, returned as
both structured content and equivalent JSON text. Public errors use fixed codes.

Resources `oracle://market`, `oracle://predictions`, `oracle://status` support
`resources/subscribe` and `resources/unsubscribe`. Notifications invalidate a
snapshot: read the resource again for current content. Changes are coalesced;
this is not guaranteed delivery of every tick. History provides durable recovery
using `next_after`. A slow/failed notification drops that client's subscriptions
after a bounded timeout. Reconnect, re-read and explicitly subscribe again. EOF
cancels the watcher. No replay or subscription state survives a client process.

## Archive and lifecycle

The historical archive preserves consumed public observations, issued forecasts
and outcome or gap records. Event sequences support pagination; original events
are not rewritten by duplicate receipts. This is Oracle's historical event store,
not a claim that sampled prices are exchange trade OHLCV. Do not import them into
the existing OHLCV snapshot store with fabricated volume. Create a consistent
immutable SQLite snapshot and retain its SHA-256 receipt for backups or research:

```sh
/Users/mitch/.venvs/soloracle/bin/soloracle snapshot --out /Users/mitch/.local/share/solmargintrader/oracle/snapshot-20261110.sqlite3
```

The command refuses overwrite and checks SQLite integrity. Backups are local
unless copied to an independently protected destination. There is no automatic
cloud publication or retention deletion.

Guide routing checks paths and hashes reference bytes. Retrieved prose never
changes policy. `--repo` identifies the source repository for an installed service;
missing guides remain unavailable. Existing skills and the private llms concept
family are read-only references. Lifecycle routing is Backtester per-coin evidence
→ prospective paper evaluation → independent live readiness. No arbitrary sample
count proves solvency or authorizes live launch. With an explicitly configured
manager home, Oracle reads the Bot Manager's own saved status; Bot Manager retains
runtime and P&L ownership. Unknown evidence remains unknown. Key presence never
proves authentication or transaction capability. Oracle does not modify signing
custody, trading subscriptions, bot settings or live arming.

Veto output carries a reason, issuance, expiry and `enforcement=false`. It
conservatively blocks its own live recommendation; other executors retain their
own policy. Integrating and verifying veto consumption in a money-moving executor
is a separate gate, not functionality implied by the existence of this response.

## Verification

```sh
/Users/mitch/.venvs/soloracle/bin/python -m unittest discover -s oracle/tests -t . -v
/Users/mitch/.venvs/soloracle/bin/python -m pip check
ruff check oracle
```

The suite uses temporary archives and simulated observations. It checks
prospective issuance, source/version isolation, restart/dedup, gaps, archive
integrity, vote boundaries, malformed feeds, secret redaction, real SDK stdio
round trips, subscription isolation, timeouts and teardown. Tests do not establish
a profitable edge, verified upstream Jupiter event time, an authenticated live
account, or enforced execution veto.


The controller integration adds an inert archive reader and selected-voter MCP
views. Exact `home/oracle/ASSET/history.sqlite3` archives bind to their control
home automatically; `--control-home /absolute/home` makes that binding explicit.
Tools, resources, subscriptions and advisory veto use the same operator selection.
Missing required selection adapters fail unavailable. Forecasts, resolutions and
recorded policy identities remain bound to their original archive. Current
evaluator source changes establish a new identity and require a new archive for
writing. Existing pinned installations and archived evidence retain their original
source identity. A writer refuses an incompatible policy before schema migration;
an archive that lost its policy cannot acquire a new identity over existing data. See
`docs/ECOSYSTEM-CONTROL-ROOM.md` for current operating commands and scope.

## TradingView → Jupiter ZEC perpetuals

The Jupiter path uses GUM Beta perpetuals and preserves long/short direction.
An opposite signal closes the old side and verifies the result before opening
the new side. Same-side signals do not pyramid. The leverage, allocation basis,
owner and account must be configured explicitly. Dry-run remains the default;
the forecast service stays read-only. Read [the execution contract and account
requirements](../docs/JUPITER-ZEC-WEBHOOK.md) before activation.

Read current market health and the owner's GUM accounts without signing:

```sh
soloracle jupiter-preflight --owner OWNER_PUBLIC_KEY
```

GUM collateral is separate from Solana and Coinbase balances. A missing account
or balance is a provisioning prerequisite; no automatic deposit is implied.

For example, after choosing 2x and a 75% collateral allocation, preview newly
received signals against a funded dedicated account:

```sh
soloracle webhook --inbox /absolute/private/path/gum-signals.sqlite3 --secret-file /absolute/private/path/webhook.secret --jupiter-perps --owner OWNER_PUBLIC_KEY --trading-account CROSS_ACCOUNT_PUBLIC_KEY --subaccount-id 0 --leverage 2 --allocation 75 --allocation-basis collateral --max-slippage-bps 10
```

Allocation uses percentage units (`75` means 75%). `notional` uses the same
percentage as a position-size budget instead. Add `--live --key-file
/absolute/private/path/keypair.json` only for deliberate live operation. The key
file must be private and match the configured owner. Default operation never
loads it. Use a separate inbox from Coinbase and from previous dry-run checks;
every event binds the complete account and policy and cannot be promoted later.
Signed orders are price-capped market Fill-or-Kill Actions. No automatic account
creation, collateral deposit, leverage-preference change or transfer is performed.
Existing incompatible preferences, unsettled collateral and venue limits refuse
the order rather than changing the requested allocation.

## TradingView → Coinbase orders

The optional webhook worker treats TradingView as the trading decision. It does
not compare the signal with Oracle's predictions or apply its research, accuracy,
soak or timeframe gates. Each market buy spends **75% of available quote currency**;
each market sell sells **75% of available base currency**. Held funds are excluded.
Sizes round down to Coinbase's increment. Missing balances, unsupported/offline
spot products and quantities outside venue min/max are refused without resizing
or substituting a different currency. The manual ticket's $100 cap is separate.

The worker uses the already installed official `coinbase` CLI and its own
credential store. The authenticated MCP connector remains available for chat;
the daemon does not extract its OAuth tokens. Verify CLI access with
`coinbase portfolios list`. Pass the same portfolio UUID to the service.

Run from an environment with Oracle installed:

```sh
soloracle webhook --inbox /absolute/private/path/signals.sqlite3 --secret-file /absolute/private/path/webhook.secret --coinbase --portfolio-id PORTFOLIO_UUID
```

This default records dry-run plans and never calls order creation. Add `--live`
to enable real orders for newly received alerts. With neither `--coinbase` nor
`--live`, it acts as an inbox only. Existing inbox and dry-run alerts are never
promoted to live. Each event binds its portfolio and mode at receipt; a dry-run
service cannot dispatch old live alerts. Use a separate inbox for dry-run
checks if a live backlog exists; the oldest live event remains disarmed. One process owns an inbox. Create a
`KILL` file beside the inbox to pause new submissions; remove it to resume.
Queued alerts expire after five minutes. A signal already being submitted may
complete after shutdown or KILL; its durable receipt remains authoritative.

The secret file must be a regular file owned by the process user, mode 600, and
contain a random value of at least 32 characters. `ORACLE_WEBHOOK_SECRET` is also
supported for foreground use. Do not commit the secret or alert payload. The
HTTP receiver binds only 127.0.0.1:8765 (override `--port`). Connect an HTTPS
reverse tunnel to it and set the TradingView webhook URL to its `/tradingview`
path. Protect ingress logs and request bodies: the body secret grants order
authority, and it is not a TradingView cryptographic signature.

TradingView **strategy order-fill** alert message template:

```json
{
  "secret": "YOUR_PRIVATE_WEBHOOK_SECRET",
  "event_id": "{{ticker}}-{{strategy.order.id}}-{{strategy.order.action}}-{{time}}-{{timenow}}",
  "symbol": "{{exchange}}:{{ticker}}",
  "side": "{{strategy.order.action}}",
  "timestamp": "{{timenow}}"
}
```

Use unique stable event IDs for each intended order. The same ID and payload can
be delivered repeatedly without creating another order. Multiple intended fills
within the same second with the same strategy order ID need a unique ID generated
by the Pine script. Indicator alerts should set `side` explicitly to `buy` or
`sell` and use their own unique ID. Exact pairs (`SOL-USDC`, `SOL/USD`) and Coinbase
compact tickers (`COINBASE:SOLUSDC`) are supported. Chart exchange prefixes are accepted, but Coinbase must offer the exact pair;
ambiguous symbols are refused. The service never changes USDT into USD or USDC.

The receiver validates timestamps (Unix seconds or UTC `YYYY-MM-DDTHH:MM:SSZ`),
accepting events up to five minutes old or 30 seconds ahead. HTTP 202 acknowledges
receipt; it does not mean Coinbase filled an order. Order dispatch runs separately.
Read persisted outcomes with:

```sh
soloracle webhook-status --inbox /absolute/private/path/signals.sqlite3
```

The service commits the size and deterministic client order ID before its single
create call. Unknown submissions and pending orders block subsequent submissions.
Read-only order lookups reconcile known order IDs. If an interrupted submission
has no saved order ID and the CLI omits client IDs, it stays unknown; an empty
order search never proves no order was placed. Inspect Coinbase before resolving
that condition. A replay never automatically submits again. Fills and fees come
from order lookup rather than a forecast or estimated profit.

Local tests cover authenticated reception, real loopback HTTP, 75% rounding,
pagination, single submission, crash states, ambiguity and reconciliation. Those
checks do not prove an actual TradingView alert or live fill. No real order is
needed to test the transport; use the default dry-run mode for delivery checks.

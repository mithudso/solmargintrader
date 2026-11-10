# Oracle 0.2.0

Oracle is a local shadow signal service, defaulting to SOL/USDC. Explicit
`--instrument BTC/USD` (or another supported symbol/quote) binds each archive,
CLI and MCP process to that instrument. No quote conversion is implied. A single foreground daemon
consumes source-labelled observations into a durable historical SQLite archive.
It evaluates 14 existing strategy cards prospectively and serves snapshots,
history, guide routes, readiness and resource subscriptions through MCP.
It never loads signing keys or submits orders. Live readiness is blocked and
vetoes are advisory: no existing executor consumes them in this release.

## Install

Python 3.13 or newer is required. Install the canonical backtester and Oracle
in their own environment. Bot Manager is an optional read-only integration.

```sh
python3 -m venv /Users/mitch/.venvs/soloracle
/Users/mitch/.venvs/soloracle/bin/python -m pip install /Users/mitch/dev/solmargintrader/backtester /Users/mitch/dev/solmargintrader/oracle /Users/mitch/dev/solmargintrader/botmanager
/Users/mitch/.venvs/soloracle/bin/soloracle --help
```

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
Twenty resolved calls are required by default. Below 60% accuracy a strategy is
excluded from voting while shadow predictions continue. At exactly 60% it is
eligible. Weight is hits/resolved. More than 100 hits doubles that weight, so a
perfect 101/101 record carries 200% of one vote. Exactly 100 hits does not double.
This is the documented provisional interpretation of the owner's bonus rule.

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

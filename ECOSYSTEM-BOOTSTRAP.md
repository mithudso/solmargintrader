# Install and start the paper ecosystem

One script installs the headless components into a dedicated environment,
checks their installed interfaces, acquires history, backtests the frozen
strategy/coin matrix and automatically hands usable results to prospective
forward testing. It also starts per-coin Oracle evaluation and registers every
requested paper trial. It never arms a bot or starts a live execution component.

## Start

Python 3.13 or newer and network access are required. From any directory:

```sh
python3 /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py start
```

No arguments also means `start`. The script installs five local projects:
backtester, Oracle, Bot Manager, the headless SolTUI research runtime, and the
ecosystem supervisor. It uses `/Users/mitch/.venvs/solecosystem-0.1.3` by default.
Version 0.1.3 coordinates manager 0.4.0, canonical backtester 0.1.1, Oracle 0.2.1
and headless research-runtime 0.1.2. It preserves schema 4 telemetry. It does not
upgrade or stop the existing /Users/mitch/.venvs/solecosystem-0.1.1 or
/Users/mitch/.venvs/solecosystem-0.1.2 environments or their immutable experiments. Continue an existing run with
that environment's installed `solecosystem` entry point; select a fresh reviewed
environment and home for changed source rather than rewriting its receipts.

It bundles the local web control room. It does not install the native macOS app,
extension browser integration, wallet signing paths or the archived liquidity
service. It does not alter shell profiles
or use remote shell installers. `--venv /absolute/new/environment` selects another
dedicated environment. Foreign environments are refused. A completed environment
with changed source is refused; choose a new environment rather than upgrading a
running experiment. Interrupted first installations can resume.

The health check uses installed imports from a temporary working directory,
checks package versions and both strategy catalogs, and connects a real official
MCP client to the installed Oracle server. No-data must remain unavailable; the
stdio process must close cleanly. No provider key or wallet is loaded by this check.
A health receipt proves these checks, not live trading capability.

The default run home is
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1`. Dates and selections are
frozen there before the detached supervisor starts. It survives closing the
terminal. Repeating `start` resumes that same plan and does not create another
worker. After a reboot or supervisor crash, repeat `start`; OS auto-start is not
installed by this script. Stop requests are scoped to the recorded instance and
batch. Another component's recorder and trading state are retained.

## The default matrix

The owner-selected universe contains BTC, ETH, SOL, XRP, HYPE, DOGE, LINK, NEAR,
SUI, AVAX, JitoSOL, KMNO, USDC and XMR. Symbols are canonicalized uppercase. All
34 registered backtester strategies are enumerated explicitly; `--strategy all`
in the older backtester CLI is not used because it means a smaller default set.

Defaults are daily bars, the `medium` card preset, history from 2025-01-01 to the
start of the current UTC day, and paper/disarmed operation. This produces
14 × 34 = 476 requested cells. Larger intervals/preset matrices can take hours or
longer. Every cell remains visible even if its data or runner is unavailable.

The frozen `costed-shadow-v1` research policy sets `research_min_confidence=0`:
it scores raw strategy signals with the existing fees, slippage and borrow
scenario. It remains unleveraged and long-only by default. This paper baseline
exists to measure hypotheses, including losing ones. It does not use past accuracy
as a profit probability or provide live readiness. `--research-min-confidence 0.8`
selects a separate confidence-gated experiment; configurations may then produce
no trades and remain unevaluable. Both historical and forward settings are saved
in the batch, including the confidence gate. No existing experiment is rewritten.
The reused F5 engine models the documented Jupiter Perps cost scenario at 1x on
these Coinbase reference bars. Those costs are assumptions, not historical
venue quotes or a claim that each asset has a tradable Jupiter perp market.

The initial integration run is retained at
`/Users/mitch/.local/share/solmargintrader/ecosystem`. It inherited the owner's
80% simulation gate and produced zero-trade results. Its failed results were not
promoted. The new default home and environment above identify the explicit paper
baseline separately. This changes no live trading settings or Oracle vote policy.

```sh
python3 /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py start \
  --home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1-expanded \
  --intervals 1m 5m 15m 1h 6h 1d --horizons short medium long
```

`--coins BTC SOL`, `--strategies rsi ma_crossover`, `--start` and `--end` narrow an
explicit new experiment. `--end` is exclusive. Once a home has a plan, changing
its configuration refuses; use a new `--home`. Resume without date flags keeps
the original end date rather than silently extending the experiment.

## Data and backtest gates

The default data provider is public Coinbase Exchange **asset/USD** OHLCV.
This is explicitly reference research, not Jupiter asset/USDC execution data.
The script does not assume a stablecoin conversion or relabel another venue's
cache. Existing historical packages with different quotes or provenance remain
untouched. Each download needs complete requested bounds, closed candles,
contiguous intervals and a matching source/hash receipt. A cached file without
that proof is not accepted. Downloads and their receipts are immutable.
Only verified accepted copies enter the F5 data directory.

Some of the 14 assets may not have Coinbase USD markets or enough history for
the requested bounds. Those downloads are reported `blocked`; their matrix
cells remain missing/unsupported. This is not an all-assets-success claim.
`--offline` validates proven cached data, creates the frozen batch and registration
ledger, then stops at `offline_prepared`. It starts no batch, recorder or forward
network requests. It requires an already verified environment and never runs pip
or downloads dependencies. Offline preparation does not claim that backtests ran.

The existing F5 worker owns costed CPCV evaluation, durable attempts and result
selection. No new optimizer or competing backtest queue is created. It waits for
all requested backtest cells to reach terminal states before handing usable
selected configurations to its isolated prospective forward ledger. Failed or
unsupported cells do not become passing results. Partial coverage is reported
as `forward_partial` or `forward_partial_waiting`. Leverage-tier cards and cards
with unsupported external data retain their real runner limitations. Selected
CPCV performance is selection evidence, not independent validation or live approval.

A failed acquisition cannot be repaired by changing inputs under an already
frozen batch. For newly available markets or repaired history, choose a new home.
An interrupted unfinished acquisition or backtest resumes its existing receipts
and attempts. A crash after the owner commits an unstarted plan but before the
supervisor saves its ID adopts that sole exact plan. Partial, ambiguous, active
or changed plans are preserved and refused. A changed evaluation code identity
requires a new experiment.

## Oracle and registration

The supervisor uses the existing recorder's singleton helper with installation
disabled. It reuses a running recorder or starts its existing detached recorder;
it does not rewrite shared LaunchAgent settings or launch a competing recorder.
`--no-recorder` disables that start/recovery behavior. Only actual exact pairs such
as BTC-USD enter that coin's Oracle archive. Missing markets remain unavailable.

Each coin gets its own instrument-bound Oracle archive under `oracle/COIN/`.
Oracle's 14 selected price-only cards are separate from F5's full 34-card research
registry. It begins issuing forecasts only after genuine completed sampled bars
satisfy warm-up. Fresh observations alone do not establish a forecast, and
historical backtest scores are never inserted as forward hits. Missing quotes,
stale data and insufficient history produce unavailable states. Predictive
agreement is not a probability of profit. Jupiter API credentials are not needed
for this explicitly Coinbase USD reference workflow. Verified Jupiter streaming,
authenticated live trading and executor-enforced veto remain separate gates.

Use the installed MCP server with a coin's exact archive and instrument, for example:

```sh
/Users/mitch/.venvs/solecosystem-0.1.3/bin/soloracle-mcp \
  --archive /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1/oracle/BTC/history.sqlite3 \
  --instrument BTC/USD --repo /Users/mitch/dev/solmargintrader
```

The server is local stdio and starts for its client; the supervisor does not
pretend an unconnected stdio process is a listening network service.

`registrations.sqlite3` assigns a stable UUID to every frozen batch cell.
Identities include coin, strategy/version, interval, preset, owner and evidence
references. Restart does not register duplicate bots. Only actual trial and call
records establish forward-test activity. Worker liveness, forecast freshness and
lifecycle stage remain distinct. All registrations stay paper/disarmed. Bot
Manager reads them as externally owned trials; it does not fabricate unsupported
manager bot types or seize the F5 worker.

```sh
/Users/mitch/.venvs/solecosystem-0.1.3/bin/solbot \
  --ecosystem-home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1 status
```

## Observe, stop and recover

```sh
python3 /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py status
python3 /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py registrations
python3 /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py telemetry
python3 /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py stop
```

`state.json` records acquisition receipts, phase, batch identity, heartbeat,
per-coin Oracle availability and registration coverage. `supervisor.log` and the
run-owned F5 worker log retain progress. The batch's own SQLite ledger and
forward ledger remain authoritative for completed work. A start request or PID
alone is not progress. Check `supervisor_running`, batch counts, forward-check
coverage and actual registered call evidence. Stop is cooperative and may wait
for a bounded provider request or the current evaluation checkpoint. It retains
all results and does not stop the shared recorder.

## Local control room and manager telemetry

The supervisor binds a read-only control room on `127.0.0.1` at an available port.
The start response and `state.json` publish the actual `ui_url` after the bind.
It reuses the accepted design in `docs/design/bot-control-room/`: fleet and
inspector, evidence, Oracle and owner activity. It shows actual counts, source
timestamps and unavailable states. There are no example profits, order buttons
or promotion controls. Bot Manager retains operation and P&L responsibility.
Stopping the supervisor closes its embedded UI. A separately started viewer can
observe retained evidence:

```sh
/Users/mitch/.venvs/solecosystem-0.1.3/bin/solecosystem-ui \
  --home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1 --port 8768
```

Then its URL is `http://127.0.0.1:8768`. This is a local service, without remote
authentication or TLS. It refuses cross-origin reads, foreign Host headers,
writes and arbitrary file paths. Do not expose it through a public proxy.
`/health` proves HTTP liveness only. `/api/status`, `/api/registrations` and
`/api/telemetry` return version-1 JSON envelopes. Registration pages use a stable
bot UUID cursor; telemetry pages use a monotonically increasing sequence cursor.
The UI keeps at most 100 recent events in view and follows bounded pages. It
reports omitted history and backlog instead of presenting the first page as all
events. A lost HTTP connection retains an unavailable banner until reads recover.

The bridge reads the manager's native specification-event and runtime-event
SQLite journals. It mirrors sanitized structured events into its own durable
`telemetry.sqlite3`, with independent source cursors and provenance. Each sync
reads at most 1,000 rows per source; subsequent cycles drain backlog. A replaced
or regressed source journal becomes unavailable and never silently resets its
cursor. `--manager-home` selects a manager store explicitly; otherwise the
manager's own `SOLBOT_HOME`/`data_home()` convention applies and is frozen in the
plan. Original journals remain unchanged. The bridge creates no manager bot or
worker. Freeform log text and credentials do not enter browser responses. A
configured owner log sink contributes bounded metadata and a digest; an absent
sink remains unavailable. This integration cannot report logs that the manager
does not persist.

Oracle rows retain their own observation time, source kind, forecast horizon and
expiry. The displayed signed percentage is weighted vote balance, not profit
probability. A fresh supervisor heartbeat alone never makes an old market or
forecast current. There may be no aggregate vote until warm-up and resolved
directional evidence meet the Oracle policy. The native journals and per-coin
Oracle archives remain the authoritative full history.

## Verification

```sh
python -m unittest discover -s ecosystem/tests -t . -v
python -m unittest discover -s oracle/tests -t . -v
PYTHONPATH=botmanager/src python -m unittest discover -s botmanager/tests -t botmanager
ruff check ecosystem oracle scripts/bootstrap_ecosystem.py
```

Tests use temporary stores, controlled subprocesses and simulated feeds. They
cover matrix freezing, provenance, cache mutation, installation interruption,
concurrent starts, stale generations, atomic input publication, registrations,
owner boundaries, telemetry redaction/pagination, HTTP origin isolation and the
backtest/forward handoff. Installed acceptance must also
exercise a clean dedicated environment and actual MCP transport. A simulated
handoff does not prove that every real market is available or profitable.

## Recorded installed acceptance

At 2026-11-10 02:59 UTC, the installed 0.1.1 service completed the actual public
Coinbase acquisition and historical matrix, then automatically entered
`forward_partial`. This is observed integration evidence, not a fixture:

- 476 unique registrations remain paper, disarmed and not live-ready.
- 189 historical cells completed, 90 were partial, 155 lacked data and 42 were
  unsupported. The partial cells retain their selected-variant limitations.
- Nine supported assets each recorded 31 prospective calls: 279 unresolved calls.
  Their target times follow issuance. No matured accuracy or profit is claimed.
- All nine accepted input hashes match their receipts. All fourteen Oracle
  archives pass SQLite integrity checks. Oracle is collecting observations;
  aggregate forecasts remain unavailable during warm-up and evidence collection.
- The manager bridge mirrored seven native events. The manager has no configured
  freeform log sink, so raw log coverage remains unavailable.
- Independent verification compared 166 installed Python/web files to source,
  checked all registration pages, inspector/evidence, real manager events,
  loopback/origin isolation, narrow layout, disconnect/reconnect and a clean
  browser console. The installer separately verified actual MCP transport.

The local receipt is
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1/acceptance-receipt.json`.
The installed source fingerprint is
`4380b1649a834ebc528b3caf362a9d62149bf41a82b92de55d7dbe728e964779`.
The recorded run is `6eb651de85bd4aaba6805cfd0511217c`; the F5 batch is
`a119fc4eee48437fa0f8e9d1a73bf5a3`. Current progress may differ from this dated
receipt. The supervisor and F5 worker remain running; the URL in current status
is authoritative after a restart.

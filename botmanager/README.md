# Solbot manager 0.2.0

The standalone `solbot` CLI creates persistent named bot drafts and inspects their
pinned settings. It defaults to paper, disarmed, Solana spot, long-or-flat SOL/USDC.
An explicit supervisor runs independent grid reference-paper accounts from a
pinned Coinbase recording. Creating a draft cannot start a process, fetch prices,
initialize another component's database, load keys, or trade.
Arbitrage reports `Solana adapter unavailable`. Council is external-only.

## Install and use

Python 3.13 or newer is required. The manager uses the standard library and the
exact local `solmargintrader-backtester==0.1.0` package, which declares NumPy and
Pandas. Building uses setuptools. Install both local projects in a stable environment:

```sh
python3 -m venv /Users/mitch/.venvs/solbot
/Users/mitch/.venvs/solbot/bin/python -m pip install /Users/mitch/dev/solmargintrader/backtester /Users/mitch/dev/solmargintrader/botmanager
/Users/mitch/.venvs/solbot/bin/solbot help
/Users/mitch/.venvs/solbot/bin/solbot create grid --name sol-grid --set range_pct=10
/Users/mitch/.venvs/solbot/bin/solbot create grid --name sol-grid-wide --set range_pct=25
/Users/mitch/.venvs/solbot/bin/solbot list
/Users/mitch/.venvs/solbot/bin/solbot config sol-grid --effective
/Users/mitch/.venvs/solbot/bin/solbot status sol-grid
/Users/mitch/.venvs/solbot/bin/solbot status sol-grid --why
```

The installed console script resolves the package from its environment; it does
not require a repository working directory or `PYTHONPATH`. Each invocation emits
a JSON envelope with `schema_version`, a new UUID `request_id`, `ok`, `data`, and
`error`. `--help` provides conventional parser help. Exit codes are 0 for success,
2 for invalid input or identity conflicts, 3 for an unavailable capability, and 4
for operational/store errors. Input errors never repeat submitted values.

Settings use `--set key=value`. JSON scalar types remain exact: `armed=false` is
a boolean; `deadband_bps=0` is zero. Enum strings may be unquoted, for example
`spacing=arith`. Integer fields reject strings, booleans, and fractional numbers.
Unknown keys, NaN/infinities, duplicate settings, invalid ranges, `armed=true`,
and non-paper modes refuse before a draft is saved. `start` and `stop` resolve
identity, then return `runtime_not_available` for manager drafts without registered input. Their presence
in parser help does not advertise runnable manager bots; draft status advertises
only `inspect`. A UUID always identifies one draft; display names are unique
case-insensitively, ASCII, and cannot look like UUIDs.

## Status and control contracts

Each draft status has its own `schema_version=1`, inside the unchanged five-key
command envelope. `status --why` includes a JSON explanation; the option is
declared in the shared command registry. Existing status keys remain available,
including `owner` (the saved specification's owner), `observed_state=not_running`,
`capabilities=["inspect"]`, and `reason=runtime_not_available`.

`spec_owner`, the stable `bot_id`, and `config_revision`/`config_hash` describe the
saved configuration. `runtime_id`, `runtime_owner_id`, and `owner_generation`
describe an actual runtime and remain null for drafts, with `runtime_reason`.
Mode/arming, lifecycle, desired/observed state, input quality, owner reachability,
submission certainty, heartbeat/data age, evaluation/decision, blockers and next
trigger are separate dimensions. Unknown observations use `{value: null, reason:
"..."}`; missing heartbeats and results never become fresh data or successful work.
The snapshot mapper performs no I/O and does not query an owner or a clock.

`financials` keeps exposure, allocated capital, realized/unrealized net P&L and
costs null with explicit reasons. `configured_virtual_capital` is the saved
virtual-account setting and is never reserved allocation or measured P&L.
`evidence_identity` pins strategy/version, config revision/hash, venue/mints,
bar duration and execution model. Backtest, paper and live evidence have separate
records; absent dataset/proof hashes, dates, engine/cost identities and result
references remain null. No evidence certifies a proxy venue or execution model.

`action_capabilities` explains inspect, start, pause entries, stop, cancel orders,
close position and emergency stop separately. Only inspect is available for
drafts. Stopping a worker retains orders, positions, arming and journals;
cancellation, closing and engine kill/disarm require their own supported actions.
`manual_pins` preserves exact override values and provenance at the config
revision/hash. Tuning proposals are unavailable and read-only; versioned adoption
and automatic runtime edits are unavailable. Status never adopts new settings.

`botmanager.receipts.CommandReceipt` defines the version-1 per-bot control
contract for later owner adapters. No draft command emits a pretend owner
receipt. It carries distinct bot/request UUIDs, operation, runtime/owner identity,
nullable nonnegative owner generation, config revision, a symbolic
reason and one of `acknowledged`, `pending`, `skipped`, `failed` or `unknown`.
Pinned manager configurations require a positive integer revision. An external
owner without numeric revisions uses `config_revision=null` with the required
`config_revision_unavailable_reason=owner_does_not_version_configurations`.
The reason must be null when the revision is known; never invent revision 1.
Acknowledgment alone proves neither stopped execution nor cleared exposure.
All receipts serialize `safe_to_retry=false`; `unknown` additionally requires
reconciliation and never means zero exposure. Deserialization rejects forged
retry/reconciliation flags, unsupported versions/operations/outcomes and invalid
types. Metadata is immutable and restricted to token-like `detail_ref`,
`reconciliation_ref`, `owner_revision`, finite nonnegative `elapsed_seconds`, and
optional `config_hash` (exactly 64 lowercase hexadecimal characters) for an
available legacy configuration snapshot.
Arbitrary owner response bodies and credential fields are refused. Callers must
keep secrets out of every identity, reason and reference.

## Configuration contract

The resolver accepts `(strategy_id, context, overrides, shared_snapshot)`. Packaged
defaults precede exactly compatible shared settings, then explicit overrides.
Every effective field carries its source, source revision, and compatibility or
manual-pin reason. Original user overrides remain separate from effective values.
Mappings are recursively immutable. Specs pin strategy/version, venue/mints,
closed-bar duration, execution model, config revision, SHA-256 config hash and
provenance. Reads reconstruct that snapshot without resolving new defaults.
Changing settings or adopting new defaults is intentionally unavailable until an
explicit versioned update/adoption command exists.

A shared snapshot has this shape (all context fields are mandatory):

```json
{
  "schema_version": 1,
  "revision": "learned-7",
  "strategy_id": "grid",
  "strategy_version": "grid-ladder-v1",
  "context": {
    "venue": "jupiter",
    "base_mint": "So11111111111111111111111111111111111111112",
    "quote_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "bar_seconds": 60,
    "execution_model": "trigger_ladder"
  },
  "values": {"range_pct": 20.0}
}
```

Coinbase venue, different bars, missing mints, unknown schema or different strategy
version reject shared adoption and record the incompatibility. An otherwise
compatible snapshot with invalid settings refuses. Shared defaults may change
strategy parameters only; capital, order sizes, stop loss, venue minimum, mode,
arming and operating settings cannot be learned. This slice accepts snapshots
through its Python registry context only;
it does not read or overwrite existing optimizers, named profiles or owner stores.

## Default sources and semantics

The constructor snapshot is pinned to repository revision
`78468489cc968e25b87786246a5aa3edf43d2277`. Source-parity tests inspect syntax trees
without importing NumPy or starting existing applications.

| Family/version | Constructor defaults | Source |
| --- | --- | --- |
| grid / `grid-ladder-v1` | `range_pct=15.0`, `rungs=7`, `spacing=geom`, `deadband_bps=25.0`, `capital_usd=1000.0` | `/Users/mitch/dev/solmargintrader/soltui/bots.py`, `GRID_DEFAULTS` |
| dca / `safety-order-v1` | `base_order_usd=100.0`, `safety_order_usd=100.0`, `max_safety_orders=5`, `price_deviation_pct=2.0`, `step_scale=1.0`, `volume_scale=1.0`, `take_profit_pct=2.0`, `stop_loss_pct=0.0`, `cooldown_bars=0`, `min_order_usd=10.0` | `/Users/mitch/dev/solmargintrader/backtester/core/dcasim.py`, `DcaConfig` |
| trend / `sma-crossover-v1` | `fast_period=10`, `slow_period=30`, `entry_buffer_bps=10.0`, `capital_usd=1000.0` | `/Users/mitch/dev/solmargintrader/soltui/trend.py`, `TrendConfig` |
| momentum / `ts-momentum-v1` | `window=60`, `threshold=0.0` | `/Users/mitch/dev/solmargintrader/backtester/core/strategies/signals.py`, `TsMomentum` |

Application defaults (`manager-defaults-v1`) are `mode=paper`, `armed=false`,
`venue=jupiter`, wrapped SOL and mainnet USDC mints shown above, `bar_seconds=60`,
`capital_usd=1000.0` for each independent virtual account, `timezone=UTC`, and
`lot_method=FIFO`. Capital is virtual and does not change live limits. The only
accepted mint pair is SOL/USDC; bar duration is a positive integer and remains
part of the exact compatibility key. No prices, fees, credentials, balances or
decimals are fabricated as defaults.

Execution models retain their reference semantics: grid `trigger_ladder`, DCA
`safety_order_ladder`, trend/momentum `next_open`. A Jupiter venue label on a draft
does not certify a fill model, costs, market data, Trigger signing or swaps.
DCA's `$10` minimum is the retained constructor assumption, **not a verified
Jupiter venue minimum**. Future adapters must validate real observations and
venue constraints. Periods count bars; the manager does not convert hourly
research periods into equivalent minute periods or relabel Coinbase evidence.

## Storage and read behavior

The home defaults to the actual user's home plus `.config/solbot` (on this
machine, `/Users/mitch/.config/solbot`). `SOLBOT_HOME` selects an isolated home.
Construction, `list`, `status`, `config` and `help` do not create a home or database.
Existing reads open SQLite with `mode=ro` and `query_only`. Writes create the home
with mode 0700 and `/Users/mitch/.config/solbot/manager.sqlite3` with mode 0600.
No credentials belong in a spec, event or installation descriptor.

Store schema 1 uses SQLite `user_version=1`; migration 1 initializes the schema
under a write transaction. Unknown schemas fail closed. One transaction inserts
the immutable spec and its `spec.created` event. Database constraints enforce UUID,
name and source-identity uniqueness. Events have a fixed reference-only schema
and unique event IDs; arbitrary owner response bodies are refused. Config hashes
detect accidentally altered snapshots; they are not signatures.

Backup descriptor schema 1 reports the store schema, format, path, included
tables, and `sqlite_connection_backup` method. A consistent copy must use SQLite's
backup API; copying a database during writes is not the supported backup method.
This release exposes the descriptor but has no backup/restore CLI.

## Verify

```sh
PYTHONPATH=/Users/mitch/dev/solmargintrader/botmanager/src python3 -m unittest discover -s /Users/mitch/dev/solmargintrader/botmanager/tests -t /Users/mitch/dev/solmargintrader/botmanager
```

Tests use temporary homes and fresh CLI processes. They cover strict typed
defaults, source parity, compatible/incompatible learning, manual pins, immutable
reloads, transactional rollback, unique identities, corrupt/future schemas,
credential canaries and read-only filesystem behavior. Existing strategy engines
remain offline; their algorithms are unchanged and packaged for direct reuse. Legacy owner discovery and guarded delegation are
implemented and covered by isolated HTTP fixtures and owner source tests.
Acceptance against the actual installed owner remains unavailable at the default
endpoint; fixture/source evidence does not establish installed-owner control.
Multi-instance grid reference replay is implemented below. Live execution,
prospective data certification and browser integration remain separate work.

## Legacy discovery and guarded controls

`solbot discover` and `solbot status` query the configured existing SolTUI HTTP
owner. Neither command starts a service, recorder, native host, optimizer or
worker. Reads leave an absent `SOLBOT_HOME` absent. The default endpoint is
`http://127.0.0.1:8788`; override it with `SOLBOT_SOLTUI_ENDPOINT`. Only numeric
IPv4 loopback HTTP endpoints are accepted. Redirects and proxies are refused.
Each call has a total deadline, a response-size limit and sanitized errors.

Before reading or sending the API bearer token, the client verifies public
`/v1/health` reports `service=soltui`. It reads an existing, regular, owner-owned
mode-0600 `/Users/mitch/Library/Application Support/soltui/api-token`, or the
corresponding file under `SOLTUI_SUPPORT_DIR`. It never creates, repairs or prints
a token. A different service on the default port receives no credential.
`owner_unreachable`, `incompatible_owner` and `credentials_unavailable` have
`bots=null`; they never certify that an owner has zero bots.

Version-1 installation descriptors include a distinct installation ID, source,
absolute repository directory and Python interpreter, reviewed source revision,
protocol version, transport and advertised commands. The default paths follow
the existing SolTUI host installation: `/Users/mitch/dev/solmargintrader` and
`/Users/mitch/.venvs/soltui/bin/python`. `SOLBOT_SOLTUI_REPO`, `SOLTUI_PYTHON` and
`SOLTUI_CONFIG_DIR` can supply explicit alternatives. These descriptors never
execute an interpreter or assume the repository root is pip-installable.
The reviewed revision is a descriptor pin, not proof of the running revision.
A supporting owner separately reports its module source hash captured at load.
Status preserves a validated owner-reported `config_path` with
`config_path_provenance=owner_reported`. An absent or invalid owner path stays
null with `config_path_reason`; Council and older owners report no observed path.
`declared_config_path` is a separate installation-descriptor candidate, with
`declared_config_path_provenance=installation_descriptor`; it does not prove which
configuration the running owner uses.

The adapter discovers the owner's actual registry and uses its
`{ok, command, result, error}` envelopes. It reads `bots.manager_snapshot` when
present, otherwise the existing `bots.overview`. Council discovery uses
`council.status`; it never calls the mutating `council.config` command. Older
owners remain inspectable but advertise unavailable delegated controls.

Status distinguishes the saved effective `config_hash` used by the guard from
the frozen session's `active_config_hash`; a later settings edit cannot relabel
the active replay or its evidence identity. Missing active identity stays null.

External identities have the form `soltui-local:grid`. Their stable UUIDs belong
to the installation and family, not to a newly claimed manager runtime. A saved
forward session with no stop timestamp says desired `running`; its observed
state and worker heartbeat remain unknown. API health proves reachability only.
Council's own worker-lock observation can establish running/not-running, while
heartbeat age remains unavailable. Protocol-aware status preserves the exact
one-minute replay versus event-driven bid/ask semantics. Council's known fill
model remains a Coinbase next-minute-open proxy; a Jupiter reference quote does
not change its execution venue. Older owners with no execution-context fields
report null context with reasons. Status keeps financial values null with
reasons and does not certify a Coinbase replay as Jupiter paper/live evidence.

`start` and `stop` accept external identities only with the inspected
`--expected-session` (use `none` for an empty family slot),
`--expected-config-hash`, and a canonical UUID `--request-id`. The registry
handles these parameters; the CLI has no separate control logic. Reusing an ID
returns its durable receipt. A different operation or explicit expected context
under the same ID conflicts. Draft controls without registered input continue to refuse
`runtime_not_available`. Every receipt has `safe_to_retry=false`.

Controls require the reviewed owner's `bots.manager_control` capability and exact
advertised parameter contract. There is no fallback to the raw restart command.
Under the existing forward/config locks, the owner compares the expected session
and effective config, asset, venue, timeframe, execution model, mode and costs.
The owner starts the exact configuration and costs it compared; it does not
resolve defaults a second time after the guard. The global family slot cannot
be replaced by another market. An exact active
session/config returns `skipped/already_running`; it does not restart. A matching
stop records its stop time and retains exposure/arming uncertainty. These
simulation controls do not start the recorder or claim an autonomous worker.
Existing raw commands retain their original behavior; their later session
changes invalidate the guarded observation. This provides delegated control,
not ownership transfer or fencing of unaware clients.

The manager writes a separate schema-2 `controls.sqlite3` journal under
`SOLBOT_HOME` only for control requests. It commits a durable pending receipt
before submitting. The journal binds each receipt to its original request,
identities, expected session/config and a receipt checksum. Replay validates
those bindings and the operation/outcome/session relationship. Schema-1 rows
retain their IDs and bodies when migrated; their missing request binding makes
replay refuse `invalid_receipt`, with no automatic submit. A valid owner response
supplies the receipt's responding source revision; discovery cannot substitute
for that evidence. Inconsistent acknowledgment sessions yield `outcome_unknown`.
The owner writes a durable intent and outcome to its own
`bots/manager-requests.json` under the owner lock; the adapter never writes
SolTUI config/state files directly. The owner's journal binds the request
fingerprint, family, session and config. An unresolved intent blocks fresh IDs
for the same family. A lost acknowledgment or interrupted intent returns
`unknown/outcome_unknown`, performs read-only reconciliation, and never
resubmits automatically. Preserve both journals when backing up owner/manager
state. The owner's bounded journal refuses new requests at capacity rather than
forgetting an ID and risking a duplicate.

Browser inventory reports `registration_required`. Node FileStore is a separate
source and reports `discovery_unavailable` until an owner transport is registered;
its config may contain secrets and is never treated as browser state. Ownership
transfer, browser controls and live certification remain unavailable. The manager
reference runtime does not take ownership of these external instances.


## Persistent reference-paper runtime

Registering input explicitly captures a bounded immutable recording snapshot. The
manager never starts or repairs a recorder. `register-input` reads the descriptor
and recording, validates a closed contiguous interval, then stores the snapshot
with its byte high-watermarks and SHA-256 hashes in the runtime journal. The run
also pins the loaded simulator module hashes and NumPy version; changed engine
identity refuses replay. Registering
the same snapshot is idempotent. Different input or config cannot replace a run.

A descriptor contains these exact fields (the historical window and cost values
below are illustrative assumptions; they do not assert current fees or prices):

```json
{
  "schema_version": 1,
  "installation_id": "soltui-local-recorder",
  "source": "coinbase_exchange_recorder",
  "paths": ["/Users/mitch/.config/soltui/prices/2026-11-08.jsonl.gz"],
  "product": "SOL-USD",
  "quote_currency": "USD",
  "bar_seconds": 60,
  "start_ts": 1794126060,
  "end_ts": 1794126180,
  "fee_bps": 6.0,
  "slippage_bps": 2.0,
  "carry_bps_per_hour": 0.0,
  "min_order_quote": 10.0,
  "capital_quote": 1000.0
}
```

The product must be SOL-USD/USD or SOL-USDC/USDC. The reference capital's numeric
amount must equal the saved capital setting; its explicit currency is retained.
No USD/USDC exchange or peg conversion takes place. USDC results stay in
`reference_financials`; USD-named public amounts remain unknown. Accounts are
independent simulations, not reservations against one funded wallet.

Every cost and minimum size is required. These are simulation assumptions, not
observed venue fees or executable sizing. Optional typed limits default to
`max_bars=2048`, `max_quote_age_s=5` and `max_sample_gap_s=5`; neither freshness
ceiling can be loosened above five seconds. This slice accepts only one-minute
grids, at most 100 rungs, at most four recording files of 64 MiB each, and at most
256 MiB of decompressed scan. Larger inputs refuse explicitly. It never truncates
a run's history, cursor, fills or lots. Each requested bar must have coverage near
both boundaries; missing products, stale/future quote timestamps, out-of-order
arrivals, gaps and incomplete lines refuse registration.

The existing recorder supplies bid, ask and quote time. Its version-1 format does
not distinguish book from ticker provenance: the identity says
`not_recorded_book_or_ticker_unknown`. The manager retains quote age and recorded
arrival coverage and constructs **sampled midpoint** candles. These are neither
exchange OHLC candles nor executable quotes. Runs are `reference_paper` on
`coinbase_proxy`, with `sampled_mid_ohlc_resting_ladder` execution semantics. The
saved target remains Jupiter SOL/USDC `trigger_ladder` in a separate identity.
Neither the venue nor the execution model is certified for live promotion.

Example commands after saving a descriptor at the stated path:

```sh
/Users/mitch/.venvs/solbot/bin/solbot register-input sol-grid --descriptor /Users/mitch/.config/solbot/reference-input.json
/Users/mitch/.venvs/solbot/bin/solbot start sol-grid --request-id 00000000-0000-4000-8000-000000000001
/Users/mitch/.venvs/solbot/bin/solbot daemon
```

`daemon` is an explicit foreground process. `start` persists desired intent and
returns a pending receipt even when no supervisor is running. The optional UUID
lets a caller inspect the exact durable receipt after a lost response; a different
operation with the same UUID conflicts. Ordinary requests have a 100,000-receipt
limit; 100 additional slots are reserved exclusively for running-to-stopped
transitions, covering every supported registered instance, including queued
intents. New starts and new-ID no-ops cannot consume that reserve. Accepted IDs
are never forgotten. Without a supplied UUID, one is generated and returned in
the receipt. Repeated starts never replace an active worker.
`stop` persists stopped intent and fences in-flight commits before returning. It
retains positions and simulated orders implied by the canonical replay. It never
closes exposure or changes arming. Stopped intent survives daemon restarts.

The daemon takes a lifetime home lock and spawns at most four workers, each with
its own lifetime bot lock and one tick at a time. No unbounded tick queue exists.
Each tick replays at most a 2,048-bar prefix through canonical
`run_grid_backtest(close_at_end=False)`. The grid range is plus/minus `range_pct`,
matching the existing constructor. Only newly observed fills append; the complete
checkpoint, cursor and fills commit in one SQLite transaction. Restart recomputes
the same economics; old-generation and duplicate-cursor commits refuse. A corrupt
checkpoint or inconsistent fill ledger holds the run for investigation.

Workers heartbeat every five seconds. Fifteen-second stale heartbeats and ticks
are independent failure conditions. Restart delays are 1/5/30 seconds; three
failures within ten minutes hold `failed` and require investigation. A saved
running intent is not proof of a living process. `status` separates actual lock
observations, heartbeat age, evaluation timestamp/cursor, and recording age. At
the immutable input's end, the worker remains observable but reports
`waiting/reference_input_exhausted`. It does not claim prospective evaluation or
fresh Jupiter data. Additional recordings need the later prospective-data design.

`events BOT --limit 100` reads the reference journal. The local supervisor socket
is mode 0600 with same-user peer checks on macOS/Linux, a 64 KiB request ceiling,
a bounded listen backlog and monotonic whole-request I/O deadlines (0.2 seconds
for server receipt/response and one second for client connect/send/receive).
Receiving fragments never resets the remaining budget. It dispatches the same
registry for local bot controls and reads. Registration and service administration
are explicit CLI operations outside the supervisor request loop. CLI controls
write durable intent directly, so an unavailable socket cannot prevent a stop.

`runtime.sqlite3` is independently schema version 1 and must be backed up using
SQLite's backup API together with `manager.sqlite3` and `controls.sqlite3` when
present. Runtime specs and inputs are immutable; fills, checkpoints, generations,
control receipts and reference-only events are durable. There is no reset/adopt
command that silently discards a failed run or its inventory.

## Explicit launchd service

```sh
/Users/mitch/.venvs/solbot/bin/solbot service status
/Users/mitch/.venvs/solbot/bin/solbot service install
/Users/mitch/.venvs/solbot/bin/solbot service uninstall
```

Installation accepts only a non-editable package in a stable installed environment;
it rejects source imports and temporary/worktree environments. Each SOLBOT_HOME
has its own launchd label. A conflicting existing definition refuses replacement.
`status` reads the persisted definition and supervisor lock and never installs,
starts or repairs anything; launchd registration remains explicitly unqueried.
Install checks the exact launchd service target, bootstraps an absent service from
the matching definition, and confirms registration before reporting success.
Retrying a failed bootstrap therefore reconciles the retained definition instead
of treating file existence as activation. Uninstall bootouts only its own label,
confirms absence before deleting the definition, and retains all desired intent
and journals. An already absent service permits safe cleanup of its matching
retained definition; other probe failures retain the definition and report
unconfirmed state.
Other operating systems can run the foreground daemon; supervisor adapters beyond
launchd are not implemented. Tests use isolated homes, subprocesses and mocked
launchctl operations. They do not alter production LaunchAgents.

Runtime tests cover two independent accounts, lock exclusion, duplicate controls,
concurrent commit fencing, actual crash-before/crash-after commit, supervisor
SIGKILL/orphan shutdown, dead workers, hung ticks, failure holding, retained stop,
corrupt checkpoints/fills, immutable input, and canonical economics/prefix parity.
Installed package/service acceptance is a separate release gate.

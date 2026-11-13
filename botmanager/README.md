# Solbot manager 0.7.4

The supervisor detects a frozen SQLite reader as well as a frozen writer. It
defers only transient stopped-peer journal contention so its owned-process
watchdog can recover without admitting another worker or losing checkpoint state.
Other journal errors still propagate.

Run `solbot --help` for the complete ordered command walkthrough. `solbot ui open`
starts the managed suite and opens its verified local control room. The
[managed suite guide](../docs/bot-manager-managed-suite.md) covers installation,
component health and alerts, Chrome recovery, and macOS/Linux/Windows support.

**Start with the [short working quickstart](../docs/bot-manager-quickstart.md).**
Running bare `solbot` now prints help and concrete next steps. It is a command-line
program, not an interactive menu. Grid, DCA, buffered SMA Trend and time-series Momentum run against
explicit historical or prospective reference input. Saved settings support explicit editing and stopped-run adoption;
research, attributed reports, health, continuing accounts and protected learning use explicit owner/evidence gates. Autonomous Jupiter trading remains uncertified.

The standalone `solbot` CLI creates persistent named bot drafts and inspects their
pinned settings. It defaults to paper, disarmed, Solana spot, long-or-flat SOL/USDC.
An explicit supervisor runs independent reference-paper accounts from a
pinned Coinbase recording or the selected existing Oracle archive. Creating a draft cannot start a process, fetch prices,
initialize another component's database, load keys, or trade.
Arbitrage offers conditional directed Solana quote-cycle diagnosis through `cycle-check`; autonomous arbitrage remains unavailable. Council is external-only.

For troubleshooting, run `solbot diagnostics`. It writes a private ZIP under
`~/Downloads` with Python/package checks and bounded component health. The bundle
does not include configuration, environment values, wallet data, account history,
or raw logs, and it is never uploaded. Review it before sharing. Use
`solbot diagnostics --output /path/to/solbot-diagnostics.zip` to choose the file.

For the current operations and remaining evidence gates, read
[the 0.6 operations guide](../docs/bot-manager-0.6-operations.md).

For the complete implementation history, operator workflows, source ownership,
backup/recovery guidance, release evidence and remaining milestones, read
[the bot-manager handoff](../docs/bot-manager-handoff.md).

## Install and use

Python 3.13 or newer is required. The manager uses the standard library and the
exact local `solmargintrader-backtester==0.2.1` package, which declares NumPy and
Pandas. Building uses setuptools. Install the compatible local backtester, Oracle, headless research runtime and manager projects in a stable environment:

```sh
python3 -m venv /Users/mitch/.venvs/solbot
/Users/mitch/.venvs/solbot/bin/python -m pip install /Users/mitch/dev/solmargintrader/backtester /Users/mitch/dev/solmargintrader/oracle /Users/mitch/dev/solmargintrader/soltui /Users/mitch/dev/solmargintrader/botmanager
/Users/mitch/.venvs/solbot/bin/solbot help
/Users/mitch/.venvs/solbot/bin/solbot create grid --name sol-grid --set range_pct=10
/Users/mitch/.venvs/solbot/bin/solbot create grid --name sol-grid-wide --set range_pct=25
/Users/mitch/.venvs/solbot/bin/solbot list
/Users/mitch/.venvs/solbot/bin/solbot config sol-grid --effective
/Users/mitch/.venvs/solbot/bin/solbot status sol-grid
/Users/mitch/.venvs/solbot/bin/solbot status sol-grid --why
```

The installed console script resolves the package from its environment; it does
not require a repository working directory or `PYTHONPATH`. Application subcommands emit
a JSON envelope with `schema_version`, a new UUID `request_id`, `ok`, `data`, and
`error`. `--help` and bare invocation provide parser help and next steps. Exit codes are 0 for success,
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
revision/hash. Tuning proposals are unavailable and read-only; explicit versioned adoption is available only at a verified stopped reference
boundary. Automatic runtime edits remain unavailable. Status never adopts settings.

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
`edit` changes only explicitly supplied settings against the latest saved body.
It never resolves current defaults over existing fields. Shared defaults are not
automatically re-adopted.

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

## Editing, history and explicit adoption

```sh
/Users/mitch/.venvs/solbot/bin/solbot schema grid
/Users/mitch/.venvs/solbot/bin/solbot edit sol-grid --set range_pct=20 --expected-revision 1
/Users/mitch/.venvs/solbot/bin/solbot history sol-grid --revision 1
/Users/mitch/.venvs/solbot/bin/solbot apply sol-grid --expected-revision 2
```

`edit BOT --set KEY=VALUE ...` preserves the UUID, creation time, every unedited
resolved value and provenance field, and all other manual pins. Each effective
change appends a new configuration revision and hash. Pinning a previously
inherited value is a meaningful change even when the number stays the same.
Repeating an identical existing pin is a no-op. Strategy replacement and rename
are unavailable. Safety-fixed fields accept only their existing permitted values;
`armed=true`, live mode, unknown keys, invalid types and nonfinite numbers refuse
without reflecting submitted values.

`--expected-revision N` compares the saved revision inside the mutation lock.
Without it, the delta applies to the latest saved body inside that same lock.
`--request-id UUID` provides durable, replay-only idempotency. Repeating the exact
accepted request returns its original `{spec, receipt}` even after later edits or
adoptions. A different operation or delta under the same UUID refuses. Dedicated
version-1 mutation receipts identify the request, exact delta, expected/prior and
accepted revision/hash, actor UID, acceptance time, active/prior runtime and
generation where present. Receipt, immutable acceptance context, request row and
saved history must agree; a recomputed checksum alone does not permit receipt
transplants. Checksums detect corruption; they are not signatures against a user
who controls the entire database.

`history BOT [--revision N]` returns exact saved versions with save time and
request attribution, plus current and archived reference runs. Each nested run
includes its pinned spec/input, complete checkpoint and fills, events, and retained
control receipts. Legacy receipts remain inspectable with `replay_proven=false`;
they retain the existing `invalid_receipt` refusal policy. Reads never migrate or
create an absent home and every journal decoder uses one SQLite snapshot.

An active worker always uses its pinned specification. `status` retains the saved
`config_revision`/`config_hash` and adds `saved_config_*`, `active_config_*`,
`pending_changes`, `adoption_blockers`, and explicit edit/apply entries in
`action_capabilities`. Its runtime evidence and financial results describe the
active revision. The existing runtime `capabilities` list remains compatible.

`apply BOT [--descriptor PATH]` explicitly adopts the saved revision. It never
starts a worker. With no runtime and no descriptor, it records an honest
`draft_uses_saved_revision` no-op. A new descriptor uses the existing strict
recorded-input and cost validation. Existing recorded input can be reused only
when compatible with the saved strategy, timeframe and virtual capital. Changed
capital requires an explicit matching descriptor; units and costs are never
rewritten or inferred.

Replacement requires stopped intent, no held worker lock, no unresolved tick,
no failed/blocked state, and a fully reconciled zero-exposure checkpoint with no
open lots or accrued carry. The canonical replay independently confirms the
checkpoint before adoption. Tiny floating-point unrealized-P&L residue up to
1e-9 quote units is tolerated only after exact replay equality. Open exposure
remains blocked; stop does not close it. The old runtime row, fills and per-run events
are retained together in an immutable archive. The global event stream remains
append-only and carries the runtime UUID on every new event. The replacement has a new runtime UUID,
a strictly greater fencing generation, zero cursor and stopped intent. Old
control receipts replay without acting on the new run. Applying the already
active revision with unchanged input is a no-op, preserving progress and capital.

A per-home guarded flock serializes edits, registration and adoption across
processes. Runtime replacement, archival and its receipt share one journal
transaction. The configuration-request quotas are independent of control stop
capacity. Stop never waits for the mutation flock. Runtime schema 3 adds archives and adoption requests. Runtime schema 4 keeps
global event sequences monotonic across adoption and adds runtime attribution.
It preserves existing current event IDs, imports archived events above all known
legacy IDs, and records their original sequence and import origin separately.
Historical archive bodies and every schema-1/2/3 control ID, body and
legacy-context policy remain unchanged. Reads never perform this migration.
Stop can retain the prior event schema so archive import failures cannot prevent
durable stopped intent; another authorized runtime writer performs the migration. Back up all three SQLite journals using their
connection backup APIs. `history` has no retention or pagination policy yet;
large histories are intended for direct CLI use. Mutations are explicit CLI
operations outside the supervisor socket request loop.

`schema [STRATEGY]` exposes version-1 machine-readable field types, exact defaults,
units and limits from the validation definitions, cross-field constraints,
protected identity fields, current runtime/certification limits and arguments
from the actual command registry. Its `global_arguments` section also defines
root context options such as the opt-in `--ecosystem-home`; the parser uses those
same definitions. Arbitrage remains unavailable and Council is
external-only. The schema is a form contract, not certification of live trading.

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

Store schema 2 uses SQLite `user_version=2`. Authorized writes migrate schema-1
stores by copying their exact saved bodies into append-only `spec_versions`.
Schema-1 reads remain inert. Unknown or malformed schemas fail closed. One
transaction inserts the immutable spec, its version, and `spec.created` event. Database constraints enforce UUID,
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
ceiling can be loosened above five seconds. Reference families require one-minute bars; grids allow at most 100 rungs, at most four recording files of 64 MiB each, and at most
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
fresh Jupiter data. Prospective Oracle sources instead wait for newly accepted completed bins.

`events BOT --limit 100` reads the append-only reference event stream across
current and archived runs. Each schema-4 event includes its runtime UUID;
`origin_sequence` and `origin` distinguish imported legacy rows from new events.
A schema-3 mirror whose cursor already became ambiguous through prior sequence
reuse remains unavailable; the manager never resets or silently rebinds it.
Telemetry checks persisted `origin_sequence` values across both legacy-current
and legacy-archive rows. Reused IDs contribute a stable fingerprint to the source
marker, even if another bot retains the first event. Source metadata exposes
`legacy_reused_sequence_count` and `legacy_reuse_fingerprint` (null when no reuse
exists). A fresh mirror can bind the migrated stream, while a prior ambiguous
mirror retains its cursor and refuses ingestion. An unambiguous migration keeps
the original marker. Native events do not change this migration evidence.
The local supervisor socket
is mode 0600 with same-user peer checks on macOS/Linux, a 64 KiB request ceiling,
a bounded listen backlog and monotonic whole-request I/O deadlines (0.2 seconds
for server receipt/response and one second for client connect/send/receive).
Receiving fragments never resets the remaining budget. It dispatches the same
registry for local bot controls and reads. Registration and service administration
are explicit CLI operations outside the supervisor request loop. CLI controls
write durable intent directly, so an unavailable socket cannot prevent a stop.

`runtime.sqlite3` is independently schema version 4 and must be backed up using
SQLite's backup API together with `manager.sqlite3` and `controls.sqlite3` when
present. Runtime specs and source selections are immutable. Prospective inputs append accepted observations and completed bars atomically with account transitions; fills, checkpoints, generations,
control receipts and reference-only events are durable. Explicit `apply` archives
all old run evidence in the same transaction that admits the new stopped run.
Failed runs and retained inventory cannot be silently reset.

Runtime reads hold one explicit SQLite snapshot across row and fill decoding.
A concurrent valid commit cannot mix a previous checkpoint with newer fills.
The supervisor rechecks suspected integrity faults under a write lock before
quarantine; transient journal-access errors do not become permanent corruption.
Checkpoint writes and reads reconcile the complete bot/config/input/target/grid
identity and run hash against the pinned run, even for identical-config bots.

Schema-2 receipts bind the canonical request UUID and immutable acceptance context,
including the then-accepted owner/generation and prior desired state. Replay checks
the receipt against that context and the pinned bot/runtime identity; later worker
or stop generations do not rewrite historical receipts. Schema-1 runtime state
remains readable without migration. An authorized writer migrates the journal,
preserving every legacy request ID and body with a null acceptance context.
Those legacy receipts refuse replay with `invalid_receipt`: their historical
acceptance cannot be proven. They are never deleted, resubmitted or given invented
context. A fresh explicit stop still persists and fences the worker after migration.

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

## External paper registrations

`solbot --ecosystem-home /absolute/run/home status` reads registered F5 paper
trials through the optional ecosystem adapter. These remain owned by F5; this
command does not create manager drafts, claim runtime ownership or enable live
controls. See `docs/ECOSYSTEM-BOOTSTRAP.md` for the resumable installer.


## Prospective reference preparation

Use the existing shared Oracle source explicitly. Preparation never starts its
producer, recorder, a worker or a service. `shared-sol-usd` selects
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1/oracle/SOL/history.sqlite3`.
The source is Coinbase SOL/USD and the saved target remains Jupiter SOL/USDC.

```sh
solbot create trend --name sol-trend
solbot prepare-input sol-trend --archive shared-sol-usd --reference --output /Users/mitch/.config/solbot/trend-reference-v1.json
solbot data-check sol-trend --descriptor /Users/mitch/.config/solbot/trend-reference-v1.json
solbot register-input sol-trend --descriptor /Users/mitch/.config/solbot/trend-reference-v1.json
solbot start sol-trend
```

The descriptor schema is 2. It freezes the archive's policy, exact source scope,
activation clock and sequence watermark, currency, capital and cost assumptions.
The `canonical-spot-reference-v1` profile derives fee/slippage from canonical
`CostConfig`, assumes zero spot carry and a 10-unit minimum. The numbers are
simulation assumptions, never observed Jupiter costs. `--set` accepts changed
cost/coverage values. `--mode historical --start-ts EPOCH --end-ts EPOCH` captures
an explicit closed interval. Existing descriptor files are never overwritten.
`data-check BOT` returns schema 1 with actual coverage, source age, warmup,
reference units, model compatibility and missing executable evidence.

Only accepted Oracle observations after activation enter prospective evidence.
The partial activation minute is excluded; each completed minute needs observed
edges within five seconds and no intervening gap above five seconds. Prices use
the observed clock, not wall-clock fabricated candles. Traded volume is unknown;
price-only engine consumers cannot access a fabricated volume series. The source
cursor, observation bodies/hashes, closed bars and account checkpoint commit in
one fenced transaction. The input may append but cannot rewrite prior bars/lots.
A crash replays the durable page exactly. A saved stop survives restart.

A stale, absent, inaccessible or changed-policy producer holds new entries and
reports that condition separately from the worker heartbeat. Backlogs carry
`delayed_replay`, never real-time evidence. Capacity is finite: 2,048 bars and
245,760 accepted samples per account. `resource_limit` holds the original run
and inventory; it never truncates evidence or reallocates virtual capital.

DCA calls the safety-order deal simulator, including deferred same-bar TP.
Trend calls the packaged `soltui.trend.TrendFollowing`; Momentum calls
`TsMomentum`. Both use canonical next-open execution. All prefixes retain
cash, entry costs, open inventory and realized/unrealized P&L. Simulator hashes
are strategy-specific; packaging-only version changes do not corrupt an old run.
A changed economic implementation may refuse execution while inspection and
stopping remain available. No forward result establishes a live trading edge.

## Actual Solana quote evidence and cycles

`oracle.quotes.collect_quote` is an explicit opt-in shared Oracle capability,
with a required API key, exact input/output mints, integer raw input amount and
Swap v1 slippage. It performs one HTTPS GET and never retries. Its fixed shared
Oracle budget is `/Users/mitch/.local/share/solmargintrader/oracle/quote-budget.sqlite3`:
all selected coin archives share at most 60 attempts per minute. Collection is
disabled by default and no service automatically invokes it. Quote schema 1
adds append-only `quote_observations` to an existing Oracle archive; inert reads
never create or migrate it. `capture_quote`, `import_quote`, `read_quotes` and
`validate_observation` preserve source/version, amount, mints, route, context
slot, output/minimum, clocks, expiry and latency. Missing network/priority/rent
fees and unobserved fills remain explicit certification blockers.

`solbot cycle-check --descriptor /absolute/cycle.json` accepts schema 1 with
`observations`, `assumptions`, an explicit `failed_leg` (null for all-leg success),
and optional actual `unwind` observation. Each next leg's requested raw amount
must exactly equal the preceding minimum output, with matching directed mints.
All receipts must align within one second and be unexpired at evaluation.
Each observation's ID keys explicit nonnegative integer assumptions:
`network_fee_start_raw`, `priority_fee_start_raw`, `rent_start_raw`,
`failed_transaction_start_raw`, `cost_currency_mint`,
`route_platform_fees_in_output=true`, `fill_policy="minimum_output"`.
Costs must be denominated in the cycle's start mint; no conversion is guessed.
Failed legs require an exact-size, aligned unwind quote when inventory differs
from the start token. Missing/partial/stale/future/size-mismatched evidence refuses.
The result is conditional pessimistic paper P&L; `booked_profit_start_raw` is null.
Live cycles remain unsupported without atomic construction and a verifier.
No actual production route dataset or profitable cycle is claimed by this release.


### Reviewed quote and prospective safeguards

Prospective polls mark generation-fenced tick intent before archive access or
canonical evaluation. The atomic progress commit clears that marker even when
no completed bar is available. A fresh heartbeat cannot hide a hung prospective
evaluation: the existing supervisor watchdog fences and terminates it.

Quote evidence currently supports one direct route leg at 100% allocation, with
positive raw input/output amounts and exact envelope mint/amount agreement.
The collector requests `onlyDirectRoutes=true` and records
`route_policy=direct_single_leg_100pct_v1`. Split and multihop plans refuse with
`quote_route_topology_unsupported`; nonzero platform-fee topology refuses with
`quote_platform_fee_topology_unsupported` until its flow can be reconciled.
No unsupported route is silently treated as a direct equivalent.

The Swap v1 field `priceImpactPct` is retained as its exact decimal string and
labelled `unit=fraction`: `0.01` means 1% impact, not 0.01%. Missing impact is null
with `price_impact_unavailable`; it never becomes zero. Invalid/nonfinite or
out-of-range impact refuses capture/import. Missing impact can be archived as
incomplete evidence but prevents conditional cycle diagnosis. These semantics
follow the current official Metis guide:
https://github.com/jup-ag/docs/blob/main/guides/how-to-build-a-custom-swap-with-metis.mdx

## M4 research owner and blind selection (0.5.0)

`backtest` and `research` use the existing headless SolTUI `ExperimentStore` through
its registered `research.protocol` action. The manager never opens the owner's
SQLite database. The coordinated source candidate pins manager 0.7.4, research-runtime 0.4.1,
backtester 0.2.1 and Oracle 0.2.4. Installed acceptance remains a separate check. Textual is unnecessary.
The CLI launches the explicitly selected interpreter with `-I`, a clean environment,
a 120-second deadline and 1 MiB limits on each transport stream.

Use `research-setup` to generate the descriptor and capture the selected installed
owner's actual protocol/package/source identity. No Python snippet or hand-authored
JSON is required. Defaults select the current manager interpreter, its environment
as working directory, the configured SolTUI root and the existing canonical
namespace binding if present. It writes only the descriptor. Explicit
`--interpreter`, `--repository`, `--config-root`, `--authority-root` and
`--authority-id` select another reviewed installation; a conflicting canonical
root/UUID refuses. Repeating identical setup is idempotent.

The complete first-use flow is:

```sh
/Users/mitch/.venvs/solbot/bin/solbot create grid --name research-grid
/Users/mitch/.venvs/solbot/bin/solbot research-setup --output /Users/mitch/.config/solbot/research-owner.json
/Users/mitch/.venvs/solbot/bin/solbot research-register --owner /Users/mitch/.config/solbot/research-owner.json --accept-registered-roots-only
/Users/mitch/.venvs/solbot/bin/solbot research-status --owner /Users/mitch/.config/solbot/research-owner.json
/Users/mitch/.venvs/solbot/bin/solbot prepare-input research-grid --archive shared-sol-usd --reference --mode historical --output /Users/mitch/.config/solbot/reference-input.json
/Users/mitch/.venvs/solbot/bin/solbot research-plan research-grid --output /Users/mitch/.config/solbot/research-plan.json
/Users/mitch/.venvs/solbot/bin/solbot backtest research-grid --owner /Users/mitch/.config/solbot/research-owner.json --descriptor /Users/mitch/.config/solbot/reference-input.json
/Users/mitch/.venvs/solbot/bin/solbot research research-grid --owner /Users/mitch/.config/solbot/research-owner.json --descriptor /Users/mitch/.config/solbot/reference-input.json --plan /Users/mitch/.config/solbot/research-plan.json
```

The existing Oracle archive must have sufficient usable history; this flow never
starts a producer. `research-plan` selects at most two neighboring validated values
for one unpinned tunable and freezes feature-aware purge/warmup with block-bootstrap
confidence. `research` can omit `--plan` to use the same conservative default.
There is no supported independent-position-horizon claim for current reference
engines; the generated plan explicitly reports strict final eligibility unavailable.
All-pinned/unsupported tunables refuse rather than invent a search.

The descriptor's `inventory_complete` field acknowledges the registered inventory
schema; it cannot certify machine-wide completeness. Optional explicit clients
have exactly `root`, `kind` (`native`, `f5`, `bg`, `forward`) and boolean `active`
fields. Registration also discovers selected/standard native configuration roots,
the documented ecosystem F5 homes, explicit `--ecosystem-home`, and recognized
selected Oracle archive context. Omitting a list cannot remove those owners.

For a clean installation only, append `--initialize-first-authority` to the
registration command. It explicitly creates the first `ExperimentStore` and records
unknown prior history before an immutable owner-clock initialization epoch. Those
historical dates remain unavailable. Genuinely later final intervals may qualify
when required owners and relevant history are verified; the epoch never resets
canonical attempt counters. Without that option the
selected database must already exist. Status/backtest never initialize it. A missing
previously registered database refuses initialization even with the option.

The per-user binding is `/Users/mitch/.local/share/solbot-research/authority.json`
(on another account, the same suffix under that account's home). It is independent
of both manager home and owner configuration root. A new configuration root must
register against the same authority; another UUID/root cannot reset attempts or
spent dates. The per-config `research-authority.json` is a receipt, not a second
ledger. Registration is locked, idempotent and imports history before recording
its receipt. `SOLTUI_RESEARCH_REGISTRY` selects an explicit isolated namespace for
controlled fixtures; receipts in that namespace are never production-eligible.

A research plan freezes the complete bounded search and confidence policy:

```json
{
  "ranges": {"rungs": [8, 12]},
  "horizon_bars": 1,
  "warmup_bars": 1,
  "blocks": 10,
  "confidence": {"method": "block_bootstrap", "seed": 0, "minimum_blocks": 10}
}
```

Ranges cannot change manual pins. The maximum is 32 configurations including the
incumbent and 1000 evaluated cells, including doubled-cost stress cells. Geometry
is chronological 50/25/25 with purge/embargo and 10–15 blocks. Horizon and warmup
must cover every candidate's feature window. Feature purge does not prove a bounded
position horizon: current reference simulations explicitly report unsupported
independence, retain end-of-window inventory, and never manufacture completed exits.
They remain useful descriptive backtests but cannot pass strict certification.

The anonymous deterministic judge runs in an actual deny-default macOS sandbox.
It cannot read the parameter mapping or repository, inspect their metadata, access
the network, or launch another process. Unsupported hosts refuse with
`isolation_unavailable`. This is a platform requirement for research, not a fallback
to an unsandboxed judge. Reports never claim current Coinbase reference data or
Jupiter indicative quotes establish certified execution costs or profitable edge.

Known active unaware owners and incomplete imported history block fresh finals.
Participating native/F5/bg/forward clients use one optimizer lease and record read
admission before evaluation. A participating native runner must use the canonical ExperimentStore; a different
native ledger refuses before capture. Legacy installations remain unmanaged until explicitly
configured with `SOLTUI_RESEARCH_AUTHORITY` pointing to the selected canonical root;
a declaration or snapshot import does not prove that an already running old process
participates. Existing immutable F5 installations remain unchanged.

`research-status --owner … --run-id …` shows retained outcomes and coverage blockers.
`research-cancel` requests durable cancellation; `research-recover` closes an
interrupted attempt only after acquiring the shared optimizer lease. An unsealed
final remains spent after error, timeout or cancellation. Retries cannot reset it
with a new bot UUID, owner home, dataset hash or search seed.

`research-proposal --owner … --run-id …` reconciles an accepted proposal into an
immutable manager receipt using baseline revision/hash and manual-pin checks, then
mirrors that receipt to the owner. Retry reconciles an exact receipt after a crash
between databases. It never edits the active bot configuration. Stale proposal
bodies remain inspectable through owner status/proposal responses, with explicit
reconciliation refusal. Roster changes or newly imported prior exposure overlapping
the final invalidate eligibility; harmless later paper reads do not.

A valid conditional final is scoped to `registered_roots_only`, its stable namespace,
required roster revision, relevant final-history proof and attempt/alpha context.
It is never a machine-wide completeness claim. M4 only stages `pending_shadow`:
M6 must establish at least seven calendar days **and** 30 prospective-paper trades
before automatic promotion. Current uncertified data, unknown-history and unaware
client blockers remain real deployment gates.

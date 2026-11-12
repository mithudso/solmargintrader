# Solbot 0.6 operations and evidence boundaries

Version: 1.2.0
Delta: v1.1.0 to v1.2.0; add the current audit source candidate and preserve the historical 0.6 package matrix.
Delta: v1.0.0 to v1.1.0; distinguish the current 0.6 candidate from the delivered historical M4 0.5 release and align the coordinated package matrix.
Release status: check the versioned source, installed acceptance and delivery receipt linked from the handoff.

The manager defaults to paper and disarmed. A draft, an input descriptor, a running
worker, a research result, a shadow proposal and live admission are separate stages.
The current Coinbase USD reference source does not certify Jupiter USDC fills,
measured execution costs or profitable parameters. Real seven-day shadow evidence
and thirty completed comparable shadow trades cannot be supplied by a test clock.

## Release components

The coordinated audit source candidate uses the versions below. These versions
identify future source; they do not relabel existing installed environments or
establish installed, browser, billing or live-trading acceptance.

| Distribution | Source version |
| --- | --- |
| solbot-manager | 0.7.3 |
| solmargintrader-backtester | 0.2.1 |
| solmargintrader-research-runtime | 0.4.1 |
| solmargintrader-oracle | 0.2.4 |
| solmargintrader-ecosystem | 0.4.6 |
| executor | 0.2.1 |
| Chrome extension | 0.6.7 |
| Archived aero-lp | 0.1.1; daemon remains disabled |

### Historical 0.6 contract matrix

The following versions describe the original broader 0.6 candidate. Retain them
when interpreting its old evidence and installed receipts.

| Distribution | Version | Changed contract |
| --- | --- | --- |
| solbot-manager | 0.6.0 | Research, reports, health, continuing accounts, learning and owner adapters |
| solmargintrader-backtester | 0.2.0 | Canonical resumable Grid, DCA, Trend and Momentum state |
| solmargintrader-research-runtime | 0.3.0 | Canonical research admission, learning receipts and native browser bridge |
| solmargintrader-oracle | 0.2.2 | Sequence-bearing bounded quote pages; existing list API remains |
| solmargintrader-ecosystem | 0.3.0 | Compatible package pins; existing producer, control room and 50bps manual referral default |
| executor | 0.2.0 | Shared wallet authority, aggregate rails, reservations and request replay |
| Chrome extension | 0.6.4 | Profile-local browser identity and delegated paper controls; everyday installation remains separately verified |

The historical M4 research release, manager 0.5.0, was delivered separately through
https://github.com/mithudso/solmargintrader/pull/192
Its delivery does not establish acceptance of this broader 0.6 candidate.

Older immutable environments and their experiments remain separate. The executor
is optional for manager installation. The manager delegates to its selected regular
installation and never imports its signing dependencies or loads a wallet key.

## Paper use

The short executed workflow is maintained in
/Users/mitch/dev/solmargintrader/docs/bot-manager-quickstart.md. Bare `solbot`
prints help. `schema` describes actual arguments and capability reasons. Use a
unique name and a selected existing archive; preparation starts no producer.

```sh
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot create grid --name reference-grid
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot config reference-grid --effective
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot prepare-input reference-grid --archive shared-sol-usd --reference --output /Users/mitch/.local/state/sb06/input.json
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot data-check reference-grid --descriptor /Users/mitch/.local/state/sb06/input.json
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot register-input reference-grid --descriptor /Users/mitch/.local/state/sb06/input.json
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot start reference-grid
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot daemon
```

The daemon runs in its own terminal. Another terminal can read status, reports and
events, or request stop. A pending start means durable intent; inspect the actual
worker, completed evaluation and source health separately.

```sh
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot status reference-grid --why
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot report reference-grid --format human
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot report reference-grid --format csv
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot events reference-grid --after 0 --limit 100
SOLBOT_HOME=/Users/mitch/.local/state/sb06 /Users/mitch/.local/bin/solbot stop reference-grid
```

Grid and DCA additionally support `pause BOT --request-id UUID` and
`resume BOT --request-id UUID`. These change entry policy and fence the previous
worker generation. Existing exits retain their canonical rules. Trend and Momentum
refuse entry pause because their exposure model does not separate it safely.
Stopping retains simulated inventory. Cancellation, closing positions and kill/disarm
remain separate operations, available only through a supporting owner.

Ten desired-running bots use at most four worker processes. The rest are queued.
A recovering worker retains its slot during bounded retry delays. Continuing
prospective accounts archive immutable 512-bar segments and retain their original
cash, lots, costs, fill timing, pending actions and starting capital. Historical
snapshot capture retains its own 2,048-bar limit. Trend/Momentum runtime lookback
is capped at 2,048 bars, with at most 2,050 retained signal bars. Larger saved drafts
remain inspectable but refuse runtime admission before source reads or allocation.
Runtime schema 5 fences older
writers; inert reads still support schemas 1–4.

## Reports and recovery

`report BOT --run-id UUID` selects an archived run. Its P&L and configuration retain
that run's identity. Current-bot learning pointers are labelled separately. Reports
do not add independent virtual accounts into a funded wallet total. Exact currency
ledgers use Decimal FIFO; canonical reference results keep their float lineage.
Unknown marks, fees or incomplete ledgers produce null totals with reasons.
Refundable rent is an asset, not profit. USD and USDC remain distinct.

`events`, `history-page`, `run-history` and report event pages use stable sequence
cursors. Pass `next_after` to the next call; row count is not a cursor. `history`
retains its earlier full-detail compatibility contract. Prefer the page commands
for polling and use a keyed report for a selected archive. Report evidence reads
have fixed byte, row, segment and SQLite work budgets; oversized legacy histories
return `report_budget_exceeded` instead of unchecked totals. Auxiliary learning
metadata has a separate fixed budget and becomes unavailable when exceeded.

`health BOT` separates process, source, evaluation, result and evidence state.
`alerts` reports deduplicated, attributed alerts and resolution evidence. A valid
loss is not a process fault. Performance comparison remains unavailable without a
compatible baseline and sufficient observations. Reads never schedule work.

After stopping all runs and releasing the selected daemon, `backup DESTINATION`
captures the manager's SQLite journals, immutable archives, receipts, registration
references and per-database cutoffs. `restore BACKUP NEW_HOME` verifies checksums,
schemas, source dependencies and canonical research history before restoring.
An aged browser snapshot retains its original observation timestamps; restoration
does not renew the external owner or claim that remaining exposure is flat.
It starts no worker, overwrites no home and never restores or rolls back the live
research authority. Unresolved external ownership prevents a snapshot.

## Research and learning

`research-setup` probes the selected installed owner and writes its descriptor.
It does not initialize an authority. `research-register --owner PATH` explicitly
enrolls the owner and imports known prior exposure. `--initialize-first` is valid
only for a genuinely unbound namespace. A missing registered database refuses
recreation. A new home, bot UUID or seed cannot reset evidence history.

`research-plan BOT` writes the default bounded unpinned search. `backtest` remains
descriptive. `research` uses the canonical owner, frozen chronology/objective,
isolated anonymous judge and spent-final protocol. Its reference-data refusal is
a useful result; it is not a promise that an executable model has been certified.
Unsupported isolation hosts refuse instead of running an unrestricted judge.

Existing Oracle forecasts retain their original model, parameters, version, horizon
and source policy. They remain explicitly ineligible for manager training until a
verified attribution contract exists; catalog names are not silently remapped.
Incomplete ingestion returns unavailable counts and blocks proposal creation.

The learning commands collect all eligible outcome cohorts, stage an accepted M4
proposal, inspect it, start a paired prospective shadow comparison, and reconcile
promotion or rollback. The canonical owner enforces 300 comparable resolved labels,
30 completed trades, one proposal per scope/day and a 48-hour promotion cooldown.
The explicit daemon's daily job uses only a reviewed local owner descriptor and
the same canonical authority. Missing compatible accepted evidence retains the
incumbent and records a reason. It installs no separate optimizer or service.

Promotion additionally requires certified compatible research, untouched final
acceptance, actual prospective observation and worker spans of seven days, thirty
completed comparable shadow trades, healthy reconciliation and unchanged pins and
revision. Queued time, delayed replay and forged client clocks do not satisfy it.
Current reference input remains uncertified. Supported adoption requires an entry
pause and a stopped, reconciled flat boundary. It preserves losses, cash, fees,
cursor and runtime identity. Owner authorization and local publication reconcile
idempotently across crashes; they are not one cross-owner database transaction.
Rollback changes future configuration and cannot undo trades or unknown sends.

## Browser and executor owners

A compatible extension registers its stable per-profile installation UUID through
native messaging. Discovery never opens Chrome databases. `discover` and fleet
`status` expose registered browser slots. Their identity is
`browser:INSTALLATION_UUID:grid`. The owner retains its single global grid slot;
per-coin settings do not create independent browser workers.

Browser start/stop require the inspected generation, configuration hash and durable
request UUID. `browser-receipt UUID` reconciles pending, acknowledged, skipped,
failed and unknown outcomes. A later stop revokes queued starts. An offline owner
is unknown; an armed or non-dry-run owner is unsupported for manager paper control.
Ownership transfer remains unavailable without both owners' fencing protocol.
Isolated Chrome acceptance does not update the owner's everyday browser installation
or its native manifest.

`executor-setup --interpreter ABSOLUTE_PYTHON --home ABSOLUTE_HOME --output PATH`
probes a regular executor installation and creates a reviewed descriptor without
enrollment or keys. `executor-capabilities --executor PATH` reads that identity.
The existing executor registry owns explicit wallet enrollment and its portfolio
cap. A new client home cannot create a separate wallet risk budget.

Exact intents bind caller UUID, runtime/generation, configuration, strategy/version,
mints, timeframe, source/cost model, installed owner and research/shadow evidence.
Reservations and aggregate strategy position/trade/daily-loss rails live in the
executor's shared wallet authority. Unknown sends retain reservations and are never
automatically retried. Keyless dry-run tests establish the guard, not live trading.
The current source has no certified evidence issuer. Manager specifications support
only paper/disarmed operation and refuse live delegation even when a caller supplies
a live flag. Trend/Momentum next-open
intents are the supported guarded preview construction; Trigger, Swap V2, Grid/DCA entry
ladders and non-atomic arbitrage remain unsupported. Existing verified reduce-only
recovery retains its separate executor rules.

## Maintenance and acceptance

Maintain one manager registry and the established component owners. Refresh exact
package pins together, build a fresh regular environment, compare loaded hashes,
and test outside the checkout. Preserve old environments, source producers,
research histories, held reservations and the stopped default demo.

The release record in /Users/mitch/dev/solmargintrader/docs/bot-manager-handoff.md
separates source tests, independent review, installed behavior, final CI and merge.
The Oracle contract is maintained in
/Users/mitch/dev/solmargintrader/docs/bot-manager-oracle-interface.md.

The existing graphical control room continues to delegate edit, apply, start and
stop through the manager registry and its durable action ledger. This release
supplies the full 0.6 backend contract for future Oracle screens; it does not claim
that every new command has a graphical workflow.

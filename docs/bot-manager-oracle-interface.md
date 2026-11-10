# Bot Manager interface and implementation report for Oracle

Version: 0.1.2
Delta: Expose registry-derived global arguments and explicit legacy event-reuse continuity metadata.
Delta: Integrate PR185 external registrations, append-only runtime schema 4 and current selected Oracle source.
Delta: Initial consumer contract for immutable editing over the delivered M1/M2 runtime.
Owner request: complete all remaining milestones, add editing and report the result to Oracle for a visual interface.
Architecture authority: `/Users/mitch/dev/solmargintrader/docs/superpowers/specs/2026-11-09-bot-manager-design.md`.
Implementation order: `/Users/mitch/dev/solmargintrader/docs/superpowers/plans/2026-11-09-bot-manager.md`.
Operations guide: `/Users/mitch/dev/solmargintrader/docs/bot-manager-handoff.md`.

This document is the maintained handoff between the manager implementation and
the later Oracle visual-interface work. Update its version and capability table
at every manager release. A future command or an illustrative UI control is not
evidence that its backend is available. The implementation epic remains open
until its required work and applicable acceptance gates actually pass.

## Authority and source maintenance

The graphical interface is a client of the manager. It must not create another
supervisor, recorder, optimizer, signer, P&L book or strategy implementation.
The manager registry owns bot specifications, lifecycle requests, receipts and
runtime evidence. Existing SolTUI, browser and executor installations remain the
execution owner of their own bots until a supported, receipt-backed transfer.
Oracle supplies labelled observations, predictions and guidance; it does not own
manager fills or decide that a vote is profit.

Maintain manager commands in
`/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/registry.py`, typed
settings in `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/config.py`,
immutable identity in `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/domain.py`,
saved revisions in `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/store.py`,
mutation bindings in `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/mutations.py`,
runtime evidence in `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/ledger.py`,
and read models in `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/status.py`.
Do not edit the SQLite bodies or hashes from a UI.

## Current access and discovery

The stable executable is `/Users/mitch/.local/bin/solbot`, a symlink to
`/Users/mitch/.venvs/solbot/bin/solbot`. The regular installed Python is
`/Users/mitch/.venvs/solbot/bin/python`. The default manager home is
`/Users/mitch/.config/solbot`; isolated clients/tests use `SOLBOT_HOME` explicitly.
Bare invocation prints help. Ordinary command output is JSON, not an interactive
menu. A start receipt alone does not prove a running worker; an explicit daemon
or explicitly installed service owns workers.

Read `solbot schema` for actual field/default/type/constraint metadata and the
registry's command arguments. Read `solbot help`, `list`, `discover`, and
`status BOT --why` for the selected installation's capability and state. Do not
infer browser state from Node FileStore or inspect Chrome databases externally.

`schema.global_arguments` describes registry-owned connection options such as
`--ecosystem-home`. The CLI parser and context extraction use that same metadata.
Keep connection context separate from individual command parameters.

The local supervisor socket is same-user, mode 0600 and bounded. It is not a
public HTTP API. Long edit/application/capture operations remain outside its fast
request loop. A future graphical backend may call the same application registry
or invoke the installed CLI with an argument array; it must retain one registry
and cannot turn shell-interpolated input into execution authority. There is no
remote web authentication or graphical API server supplied by this editing release.

## Versioned commands and receipts

Every ordinary result has exactly `{schema_version, request_id, ok, data, error}`.
Errors contain `{code, message, retryable, detail_ref}`. Exit 0 means command
success,2 invalid input,3 missing evidence/capability,4 operational/integrity
failure. Preserve nulls and their reasons. Unknown schema/capability must refuse
an operation rather than guess a compatible interpretation.

| Command after the installed executable | Consumer behavior |
| --- | --- |
| `create STRATEGY --name NAME --set KEY=VALUE` | Saves a draft with defaults and supplied overrides. Starts no worker; reserves no capital. |
| `config BOT --effective` | Reads exact saved values and provenance. This may differ from the active run. |
| `edit BOT --set KEY=VALUE --expected-revision N --request-id UUID` | Saves only the explicit delta under atomic revision CAS. Preserve unedited values/pins; never patch an active worker. |
| `history BOT --revision N` | Reads exact immutable saved bodies and attributed current/archived runs. Omit revision for all history. |
| `apply BOT --expected-revision N --request-id UUID` | Explicitly adopts at a verified stopped, owner-released, resolved zero-exposure boundary. Never starts. Optional compatible descriptor can select new input. |
| `start BOT --request-id UUID` / `stop BOT --request-id UUID` | Durable owner control. Stop retains positions and does not cancel or close them. |
| `status BOT --why` / `events BOT --limit 100` | Reads observed behavior, reason, blockers and evidence. Desired state alone is insufficient. |
| `schema STRATEGY` | Reads real editable/protected fields, current runtime bounds and certification limits. |

BOT accepts stable UUID or unique name. Strategy replacement and renaming are
not part of this editing contract. A form must retain the inspected saved
revision. A stale submission returns `stale_revision`; reload and present the
conflict to the user instead of overwriting newer settings. CLI callers may omit
expected revision to apply their explicit delta to the latest saved body inside
serialized mutation. UI forms should use CAS.

The top-level invocation ID differs from the durable mutation/control UUID.
Retain the durable receipt ID before reconciling a lost response. Mutation data
contains `{spec, receipt}`. Its receipt binds operation/delta, expected/prior/
accepted revision and hashes, actor/time, relevant active/prior runtime IDs,
generation, input snapshot identity, outcome/reason and `safe_to_retry=false`.
An exact accepted-request replay returns its original result. It cannot reapply
an old revision or control a replacement runtime. Never mint a fresh request ID
to retry an ambiguous external submit. A checksum is corruption evidence, not
an authorization signature.

## State the visual interface must preserve

- Keep bot UUID, display name, strategy version, saved revision/hash, runtime
  UUID, owner identity and generation distinct. Duplicating a specification does
  not replace a running session or reserve its capital again.
- Use `saved_config_revision/hash`, `active_config_revision/hash`,
  `pending_changes` and `adoption_blockers`. Runtime P&L belongs to its pinned
  active configuration. To display its exact rules after a staged edit, read the
  corresponding immutable history revision.
- Use `action_capabilities` for operation availability/reason. The older compact
  capability list does not include every added configuration action. Unknown or
  unavailable controls stay disabled with the backend's reason.
- Separate mode, armed state, lifecycle, desired/observed state, owner reachability,
  process/worker locks and heartbeat, input quality/age, completed evaluation,
  latest decision/reason, next trigger, evidence status and submission certainty.
  A healthy process can be waiting on stale or exhausted input.
- Stop, pause entries, cancel orders, close position and emergency stop have
  distinct semantics. Only advertised operations are available. None may imply
  the others occurred. Show remaining exposure and per-bot acknowledged/pending/
  skipped/failed/unknown outcomes after a partial fleet operation.
- Keep backtest, reference paper, prospective paper and live evidence separate.
  Never convert USD to USDC implicitly or unknown financial values to zero.
  An Oracle directional hit rate is not a probability of profit.

Successful `apply` archives the complete previous run and admits a distinct
stopped runtime. It preserves previous fills, cursor, checkpoint, events and
receipts. Reapplying an already active revision with unchanged input is a no-op.
Open lots, unresolved economics, held ownership, running intent or incompatible
input block adoption; never clear a blocker by deleting history or creating a
new bot identity automatically. Configuration editing is permitted while running,
but active execution remains pinned until a supported explicit transition.

Manager specification schema 2 and runtime schema 4 are independent from the
outer response schema 1 and external-control journal schema 2. Old saved/runtime
schemas remain readable; only authorized writes migrate them. Retain every
accepted request ID and original legacy body. Historical acceptance that cannot
be proven remains unavailable; do not fabricate missing owner context.

## Current capability boundary and remaining implementation

| Area | Editing-release capability | Remaining acceptance/work |
| --- | --- | --- |
| Configuration | Four typed draft families; immutable editing/history/schema and safe application | Later learning provenance and gated automated promotion |
| Runtime | Independent grid reference-paper accounts, recovery and explicit service controls | DCA/Trend/Momentum, prospective shared input and broader diagnostics |
| Source data | Bounded immutable Coinbase sampled-midpoint captures, explicit costs | Shared Oracle read adapter and genuine Jupiter quote evidence/certification |
| Arbitrage | Explicit Solana adapter unavailable | Conditional directed-quote paper replay; atomic construction/verifier before live |
| Blind evaluation | Approved protocol only | Isolated judge, one existing exposure owner, frozen objective/budgets, fresh final |
| Monitoring/learning | Existing operational status and reference financials | Accounting/report/load gates, all-outcome diagnosis, protected proposals/soak/adoption |
| Browser | Explicit registration required | Actual installation identity, native registration/poll, durable delegated receipts |
| Live execution | Existing executor restrictions preserved | Wallet-wide ownership/reservations, aggregate strategy risk and exact verified admission |

The owner requested every remaining milestone. They remain in the approved
order. Missing data, real elapsed shadow time, execution-model verification or
installed-browser evidence must remain visible gates; fixture success cannot
replace them. Live/Trigger/arbitrage support must not follow from a button.

## Oracle source findings to carry into the next stages

The integrated manager also accepts an explicit global `--ecosystem-home` for
read-only F5 registrations in list/fleet status. Those trials retain their owner.
Runtime schema 4 preserves an append-only attributable event stream across
application, including legacy sequence provenance. Shared telemetry must not
reset replaced/regressed cursors or reinterpret legacy null identity as proven.
Source metadata exposes `legacy_reused_sequence_count` and
`legacy_reuse_fingerprint`. A reused old event number changes the continuity
marker even when another bot retains the first event. An existing ambiguous
mirror keeps its old cursor and refuses ingestion; a fresh explicitly selected
derived mirror can consume the newly attributed stream.
Ecosystem 0.1.2 pins manager 0.3.0; existing 0.1.1 immutable environments stay intact.


At the initial dated read-only inspection, installed Oracle 0.1.0 matched source, no
default archive or daemon was observed, and the existing recorder had SOL-USD
but no SOL-USDC. An explicitly configured archive elsewhere may differ.
Oracle Price V3 records a source-labelled USD-reference ratio with unknown
upstream event time. It contains no executable route, size, fees or fill evidence.
Do not relabel it as a Jupiter backtest or profitable strategy.

Current Oracle query constructors create schema/policy when the archive is
absent. Manager discovery must use an inert read-only archive adapter or an
already selected provider. Raw history observation events can include rejected
out-of-order observations; only accepted observations belong in replay bars.
Reuse the existing producer and preserve source/policy identity. Do not start a
new recorder or silently create source state from a status page.


The current PR185 preflight supersedes the initial availability gap for its
selected source: Oracle 0.2.0 produces genuine SOL/USD observations under
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1/oracle/SOL/history.sqlite3`.
At 2026-11-10 03:38:44 UTC, a bounded read found 1,220 accepted observations and
event watermark 1,513, with 1.70-second receipt age. Read current readiness again;
these are dated observations. Reuse that existing ecosystem producer and keep
its Coinbase USD/reference/no-volume limitations explicit. The native evidence
owner does not yet govern F5's separate per-home CPCV/prospective ledgers; blind
selection must account for those exposed dates and participating-client admission.

## Visual direction and handoff delivery

The editing source is 7af12d82f4e9b8eb04262e9636487f4751730d1d. Independent installed
acceptance passed 29 checks and matched21manager plus49 canonical Python files.
Read-only inspection preserved the existing stopped demo and its old schemas.
Source validation was 136 initial tests plus 117 covering tests after the reviewed
concurrency fixes, including 9 deterministic races. These results establish the
editing/reference-runtime contract, not later milestone delivery or profitable
Jupiter trading. Full installed receipts are maintained under
`/Users/mitch/.local/state/solbot/releases/0.3.0`.

Use the approved fleet roster with a selected-bot inspector, persistent blockers
and attributable activity. Creation follows Strategy → Market/budget →
Rules/tuning → Risk boundaries → Review. Saving a draft starts no work. Preparation,
historical testing, prospective observation and live activation remain explicit
receipt-backed stages. The illustrative mockup's template list and Coinbase USD
charts do not override actual capabilities or validated schemas.

Post this report and each final capability update on the existing Oracle task,
TASK-1154, without taking its claim. The manager implementation is EPIC-1106;
editing is TASK-1178. A task comment is persistent coordination; it is not proof
that another session has read the report.

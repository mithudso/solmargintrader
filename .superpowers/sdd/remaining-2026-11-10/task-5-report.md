# Task 5 — protected learning, labels and real shadow evaluation

Status: implementation and owned source checks complete. Controller owns final registry/status/report integration, full manager release checks, installation and remote delivery. Real production shadow qualification remains pending.

## Interfaces and ownership

New botmanager.learning exposes canonical_scope, comparable_identity, classify_outcome, outcome_summary, runtime_outcomes, learned_spec, shadow_pair, reconcile_transition, learning_snapshot and record_owner_view. New learning_commands.command_specs(CommandSpec) defines learning-labels, learning-propose, learning-proposal, learning-shadow, learning-promote and learning-rollback. No public command accepts timestamps, counts, certification flags, shadow fills or replacement owner evidence. Proposal/worker creation are explicit writes; inspection and local learning_snapshot stay inert.

Canonical owner protocol adds learning-labels/propose/inspect/shadow/promote/rollback/reconcile. soltui.learning_owner stores its labels, proposal/day quotas, promotion cooldowns, paired runtime bindings, owner authorization receipts, manager publication receipts and compatible learned defaults inside the existing external canonical ExperimentStore database. It creates no new optimizer. Proposal creation consumes an existing accepted M4 research run under the existing optimizer lease. Existing M4 attempts, temporal spending, blind artifacts, fresh-final history and authority roster remain authoritative.

Canonical quota identity excludes manager-home, bot UUID, configuration fingerprint, random seed and data cost/engine fingerprints. It binds strategy family/version, venue, instrument, timeframe and execution semantics, so changing a source/model cannot reset daily/cooldown scope. A separate exact comparable identity binds source, currency, timeframe, costs, economic engine and source policy. Source/model mismatches cannot borrow label counts or evidence from another model. M4 frozen baseline, pins, engine, source/currency/cost/policy identities must match before staging.

## Labels and gates

Collection retains completed gain/loss trades, correct/incorrect resolved forecasts, data faults, execution faults and unresolved inventory as distinct cohorts. It reads validated current/archived runtime fills, including immutable segment fill history, Oracle resolved forecasts and attributed execution alerts. Comparable resolved labels count both winning and losing outcomes. Unknowns and faults do not become zero-profit observations. At least 300 resolved comparable labels AND 30 completed trades are required; one proposal per canonical scope/UTC day and a 48-hour promotion reservation cooldown are enforced by the shared owner database.

Learning permits only supported unpinned strategy parameters. Capital/order sizing, risk fields, operating mode, arming and global packaged defaults cannot be changed. Learned provenance remains distinct from manual pins. Ordinary losses never edit a configuration.

Shadow starts a fresh pair of explicitly prospective paper accounts in the same manager home. Existing supervisor/worker ownership runs those accounts; there is no second optimizer. IDs are durable before worker creation, and repeat start reuses the same two accounts. Each account binds its runtime/source activation and comparable identity. Seven elapsed days since proposal creation is insufficient: both workers need seven days since their first durable completed prospective evaluation, seven days of accepted first-to-last observation coverage across every immutable segment, only prospective delivery ranges, matching final comparison timestamps, at least 30 comparable completed exits, healthy reconciliation and a net challenger advantage. The owner also rechecks certified compatible final evidence, unchanged originating revision/runtime/pins, source certification and cooldown. Queued creation time and delayed/historical replay cannot substitute for actual prospective operation.

## Publication, recovery and rollback

The owner commits its authorization receipt before local manager publication. RuntimeLedger.learning_adopt then uses one attached DELETE-journal SQLite transaction across the local manager/runtime databases. WAL is explicitly refused rather than claiming cross-database atomicity. Publication requires explicit entry pause, a stopped/released owner, no unresolved tick and a supported flat canonical checkpoint. The continuation owner's rebind_checkpoint changes strategy geometry while retaining cash, inventory state, cumulative P&L/costs, cursor, fill history and runtime identity. A durable predecessor boundary and request/digest receipt make exact replay idempotent. Owner and manager databases remain separate transactions; reconciliation explicitly survives a crash between them.

The owner independently reads the bound manager publication journal before acknowledging reconciliation or publishing learned_defaults. A client-provided receipt alone is insufficient. Rollback stages verified prior parameter values through the same certification/clock/count/cooldown/risk and safe-account gates. It advances configuration history and never reverses trades, drops losses or restores initial capital.

## Verification

Latest manager learning suite: 9 tests passed, exit 0. Includes all outcome cohorts, ordinary-loss nonmutation, pins/risk/CAS refusals, UUID-independent scope, exact-once crash replay, inert local reads and real paired prospective worker execution through Supervisor. A canonical high-fee grid round trip realizes -43.97302098095538 and leaves cash 956.0269790190447; adoption preserves that loss, cash, fees and fills exactly.

Canonical owner learning suite: 10 tests passed before the final combined run, covering actual M4 isolated blind subprocess/artifact bindings with an explicitly controlled certified evaluator, 7-day/trade-30 conjunction, daily/cooldown scope, uncertified/delayed source refusals, queued-clock deception, public clock rejection, inert owner reads, real owner-to-manager publication/crash reconciliation and rollback. Test clock/evidence fixtures are internal injection points, not wire parameters and not claims of production elapsed time.

Combined manager learning/continuation and owner learning/research-owner regression run: 43 tests passed, exit 0, before the additional real-loss regression (which independently passed with the manager suite). Ruff checks pass for owned source/tests. Short synthetic reference data still emits the pre-existing annualized metric overflow warning; source tests do not promote it to evidence.

## Explicit limitations and production pending

Current Coinbase/Oracle reference input remains uncertified for venue execution. It cannot pass production promotion/rollback source gates. No real bot has been claimed to have completed seven days or 30 certified shadow trades. The load/clock tests use labelled fixtures; they do not establish a live trading edge.

Automatic proposal scheduling is not installed by this change. Explicit learning commands enforce daily bounds and reuse M4 results. A user-selected existing supervisor must run the shadow pair. Capacity may queue them, and the first actual worker-event clock prevents queue time from satisfying the gate. Supported configuration adoption currently requires flat state; active exposure waits explicitly rather than resetting the account. Proposal outcome ingestion rejects archives beyond its finite budget instead of accepting incomplete comparable counts.

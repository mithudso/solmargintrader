# Persistent reference-paper runtime milestone

Version:1.0.3
Delta:1.0.2 to1.0.3; verify service-origin fixtures in source and installed import modes.
Delta:1.0.1 to1.0.2; record final source and installed acceptance with immutable runtime identity.
Date:2026-11-09
Status: source and installed acceptance passed; final CI and remote delivery are the release gates.

The standalone manager now has explicit supervision for independent grid instances.
Canonical simulator code remains unchanged in the shared offline package. This
milestone proves reference replay, persistence and recovery; prospective Jupiter
feeds and the remaining new strategy adapters belong to milestone3.

## Implemented contracts

Each bot retains its specification/configuration identity, run, worker owner and
generation separately. Start is idempotent. Stop persists intent before termination,
fences in-flight work and retains lots, fills and cursor. Checkpoint corruption
cannot prevent a stop. Cursor, checkpoint and new fills commit atomically; stale
generations and repeated cursor commits refuse.

Reads use one SQLite snapshot for the run and its fills. Before quarantining a
run, the supervisor confirms an integrity error under a write lock. Transient
store failures do not establish checkpoint corruption. Checkpoints bind the full
bot, configuration, input and virtual-account identity, including when two bots
have identical settings.

The runtime journal uses schema 2. Each command binds its request UUID and receipt
to immutable acceptance context. Valid historical receipts remain valid after
later owner or generation changes. A writer can migrate a schema-1 journal while
retaining every old row and request ID. Old receipts without proven context
refuse replay and require reconciliation; they never resubmit the operation.
Reads do not migrate, and a fresh explicit stop remains available.

One explicit supervisor admits four desired-running instances, including pending
intent, and runs their lifetime workers. Each worker evaluates one
tick at a time. Process heartbeat, data age and evaluation progress remain separate.
An exhausted immutable snapshot reports waiting/reference_input_exhausted. It does
not report fresh prospective Jupiter paper. Service installation is explicit and
requires a stable noneditable environment. Reads cannot install or start it.

## Input identity and limits

The input is a declared immutable range from existing Coinbase recordings. It
pins actual product, quote currency, arrival coverage, source quote age, file byte
watermark/hash, bars, costs and engine identity. The Jupiter SOL/USDC target remains
separate. USD and USDC are not converted or assumed equal. Recorder v1 does not
identify book versus ticker provenance; that value remains explicitly unknown.

Simulation fees, slippage, minimum size and virtual capital are declared assumptions.
They are not observed Jupiter costs, executable quotes or one funded wallet. The
execution model is sampled_mid_ohlc_resting_ladder on coinbase_proxy, with no live
promotion capability.

Limits are 2,048 bars, 100 rungs, four input files, 64 MiB raw per file, 256 MiB
decompressed scan and 200,000 fills. Limits refuse rather than discard a prefix, inventory or
proof. New continuously arriving data and larger streaming runs remain later work.

## Verification

At final source 39e0c262, 109 manager tests and 42 focused runtime/paper/recovery tests
passed. The unchanged canonical simulator/card suite previously passed 87 checks. Scoped
Ruff/format and both wheel builds passed. Tests include two instances, actual
process crashes before/after commit, concurrent commits, stale generations,
supervisor death, dead/hung workers, stop retention and data integrity. Independent
task review, final broad review and the single scoped final fix review approved
the source.

CI's regular wheel installation exposed one source-origin assumption in the test
fixture. The fixture now supplies an explicit source path and checks its refusal
code. All 17 supervisor tests pass in both source and installed import modes;
independent review approved the test-only repair. Production service guards and
the accepted installed runtime remain unchanged.

Independent acceptance verified 69 loaded Python files against the reviewed
source in the stable noneditable installation. Two isolated virtual accounts
matched canonical batch fills, lots and equity after an identified worker crash.
Duplicate start retained the existing session and checkpoint. Stop retained three
lots and visible exposure; supervisor restart kept that bot stopped while its peer
recovered. At exhausted input, heartbeat advanced while cursor and evaluation time
remained fixed. Historical start-receipt replay left the stopped state unchanged.

The real empty-home launchd fixture used the stable executable. Its first uninstall
returned an unconfirmed-state error; an explicit cleanup retry confirmed job and
definition absence with the supervisor lock released. That conservative first
failure remains part of the result. All owned fixture supervisors exited 0. No
production bot, recorder, key, browser or service was changed.

An actual read-only SOL-USD/USD recording range for 2026-11-08 08:21–08:23UTC yielded
115 snapshots and two sampled bars. Its 6 bps fee, 2 bps slippage, zero carry, 10 USD minimum and
1,000 USD capital are illustrative. Source replay completed with zero fills; fixture
paths separately test economic fills and recovery. Installed bounded replay also
completed with zero fills and unchanged raw input. This short range proves no
profitable edge, executable Jupiter price or historical route coverage.

Stop capacity includes 100 reserved receipts beyond the ordinary 100,000 limit.
Only a running-to-stopped transition can use them; no-op requests cannot consume
that reserve. Accepted IDs remain durable. Service install and removal verify
launchd registration; a matching file alone is not evidence of activation.

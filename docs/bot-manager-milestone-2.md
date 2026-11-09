# Persistent reference-paper runtime milestone

Version:1.0.1
Delta:1.0.0 to1.0.1; record source fixes and approved task review.
Date:2026-11-09
Status: source task review approved; final review and installed acceptance pending.

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

At source 4b22bb1, 97 manager tests and 87 canonical simulator/card checks passed. Scoped
Ruff/format and both wheel builds passed. Tests include two instances, actual
process crashes before/after commit, concurrent commits, stale generations,
supervisor death, dead/hung workers, stop retention and data integrity. Independent task review and scoped fix review approved the source. Final broad
review, stable installed/launchd acceptance and CI/delivery remain.

An actual read-only SOL-USD/USD recording range for 2026-11-08 08:21–08:23UTC yielded
115 snapshots and two sampled bars. Its 6 bps fee, 2 bps slippage, zero carry, 10 USD minimum and
1,000 USD capital are illustrative. Source replay completed with zero fills; fixture
paths separately test economic fills and recovery. This short range proves no
profitable edge, executable Jupiter price or historical route coverage.

Stop capacity includes 100 reserved receipts beyond the ordinary 100,000 limit.
Only a running-to-stopped transition can use them; no-op requests cannot consume
that reserve. Accepted IDs remain durable. Service install and removal verify
launchd registration; a matching file alone is not evidence of activation.

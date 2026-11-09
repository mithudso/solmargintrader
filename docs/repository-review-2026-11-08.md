# Repository review — 2026-11-08

Version: 1.2.0. Delta: repair failed-transaction fee accounting and duplicate balance indices after second blind review.

## Purpose and architecture

The repository connects market-data collection, offline strategy simulation, forward evidence,
research views and guarded manual execution. It does not establish that a strategy has a live edge.

| Component | Responsibility | How it works |
| --- | --- | --- |
| `backtester/` | Offline strategy and grid simulation | Local OHLCV arrays feed a bar loop, delayed fills, costs, liquidation and metrics. Fetching is separate. |
| `research/` | Strategy comparison and decision readouts | Imports the backtester for sweeps, held-out evaluation, combinations and signal readouts. |
| `extension/` | Browser dashboard, market reads, quotes and experimental grid | MV3 service worker and UI call one command registry, also used by CLI/HTTP adapters. Trigger live signing remains blocked without a trusted intent verifier. |
| `soltui/` | macOS research console | Displays signals, predictions, paper positions and jobs; offers a separately armed manual Coinbase order path. |
| `mongo/` | Derived query store | Loads repository evidence into local MongoDB with provenance. Files remain authoritative. |
| `executor/` | Guarded Solana spot swaps | Shared CLI/API registry feeds independent price checks, rails, transaction verification, simulation, signing, write-ahead journal and one send. |
| `liquidity/` | Archived Aero LP manager | Retained source and research; owner discontinued its daemon and scout on 2026-11-08. |

The strongest design choices are the offline simulation boundary, shared command registries,
explicit trading modes and uncertain-submit holds. These are worth preserving. The main improvement
in this pass is making the persisted evidence enforce those contracts under partial writes,
malformed records and concurrent calls.

Detailed source review covered `executor/src/executor/journal.py`, `gates.py` and `engine.py`,
with immediate callers and tests. The final fee repair also changes the pure accounting dependency
`executor/src/executor/ledger.py`. Architecture orientation covered all seven components. Other
source files did not receive a full defect audit. Prior audit coverage is documented in
`docs/code-deep-optimizer-2026-11-06.md`; this review does not replace its limitations.

## 1. Per-iteration severity

| Checkpoint | Critical | High | Medium | Meaning |
| --- | --- | --- | --- | --- |
| Initial focused diagnostics | 1 | 9 | 1 | Journal (1C/2H), gates (3H), engine (4H/1M), grouped by root cause |
| Implementation review | 0 new | 1 new | 1 new | Failed auto-kill persistence and incomplete override audit writes also repaired |
| First blind gate | 0 | 2 | 1 | Clock rollback, final quote freshness and final gate-decision evidence; repaired in iteration 2 |
| Second blind gate | 0 | 1 | 1 | Failed-chain fees bypass daily loss stop; duplicate token account indices inflate fills |
| Focused post-gate repairs | 0 known open | 0 known open | 0 known open | Regression verification only; no third blind gate or independent CLEAN claim |

## 2. Findings and implemented repairs

| Pass | Source anchor | Severity | Defect | Repair and regression |
| --- | --- | --- | --- | --- |
| C1/C3/S2 | `executor/src/executor/journal.py:110`, `Journal.append` | Critical | A short `os.write` returns success before the signature is durable | Complete-write loop, no-progress/error refusal, file and directory sync; injected partial/error writes |
| C1/C3/S3 | `executor/src/executor/journal.py:154`, `Journal.records` | High | Valid JSON with invalid envelopes or kinds silently passes corruption checks | Validate envelope, finite time, sequence, kind and ID; sanitized corruption markers |
| C1/C2/C3 | `executor/src/executor/journal.py:69`, `_apply_record` | High | A malformed terminal event or duplicate intent clears an unknown send | Validate transitions/status/signature; preserve pending holds; refuse append past damaged data |
| C1/S3 | `executor/src/executor/gates.py:191`, `soak_status` | High | NaN/Infinity or malformed soak credit can approve live execution | Finite and internally consistent credit, safe reset after successful dry-run |
| C1/S3 | `executor/src/executor/gates.py:217`, `_research_results` | High | Bad schema or malformed newer failure revives an older pass | Validate the complete evidence document and refuse damaged history without rewriting it |
| P2 | `executor/src/executor/gates.py:61`, `_state_lock` | High | Concurrent gate updates erase newer failures or lose soak credit | Stable sidecar lock covers read/modify/atomic replacement; deterministic concurrent writer tests |
| C1/C3 | `executor/src/executor/engine.py:399`, `_reconcile_locked` | High | Present processed transactions become dropped after blockhash expiry | Only absent status may enter expiry handling; observed pending status remains unknown |
| C1/P2 | `executor/src/executor/engine.py:200`, `_send_live` | High | KILL arriving during journal flush misses the final send check | Recheck after both durable writes; record a definite pre-send rejection; preserve exits |
| C1/C2/S3 | `executor/src/executor/engine.py:502`, `realized_from_meta` | High | Missing token balance arrays become guessed zero opening balances | Require explicit arrays and unsigned raw amounts; missing/malformed evidence stays unknown |
| C1/P2 | `executor/src/executor/engine.py:394`, `reconcile` | High | Reconcile writes terminal outcomes outside the swap lock | Serialize all reconciliation observation and state changes with swaps |
| C2/S2/S5 | `executor/src/executor/engine.py:200`, `_send_live` | Medium | Unexpected post-send reader errors return an ordinary failed envelope | Preserve unknown, return ambiguous, record exception type without response values |
| C1/S2 | `executor/src/executor/engine.py:200`, auto-kill ordering | High | Failed KILL persistence follows a terminal result that has already cleared the hold | Write KILL before the terminal outcome; storage failure leaves send unresolved |
| S2/S5 | `executor/src/executor/gates.py:291`, `log_override` | Medium | Partial override audit writes can approve execution without a complete audit line | Complete and serialize audit writes; fail on no progress; no real override exercised |
| C1/S3 | `executor/src/executor/gates.py:217`, `_research_results` | High | Clock rollback makes a later-recorded failure lose to an older pass | Preserve both records and block nonmonotonic per-strategy timestamp history; ties still choose the later record |
| C1/S3 | `executor/src/executor/engine.py:200`, `_send_live` | High | Quote expires during final checks or durable writes | Recheck age immediately before send; negative/nonfinite age also refuses with a definite pre-send rejection |
| S5/M4 | `executor/src/executor/engine.py:200`, `_send_live` | Medium | Final gate override is logged but intent/response still carries the initial pass notes | Persist and return the final rail decision and its notes |
| C1/S3 | `executor/src/executor/engine.py:200`, failed outcome paths; `ledger.py`, `realized_pnl_usd` | High | Failed-chain fees are absent from daily loss limits | Read and journal the measured fee, include it by strategy/day, retain unknown if unavailable, and refuse old unmeasured fee records |
| C1/S3 | `executor/src/executor/engine.py:502`, `realized_from_meta` | Medium | Duplicate account indices inflate a token balance delta | Require integer, in-range, unique account indices within both pre/post arrays |

Solana documents the status contract and failed-transaction fees here:

https://solana.com/docs/rpc/http/getsignaturestatuses

https://solana.com/docs/core/fees/fee-structure

Line numbers change with integration; the named symbols and dedicated integrity suites identify each repair.

## 3. Verification gates

| Gate | Baseline | After repairs |
| --- | --- | --- |
| Executor Ruff check and format | Pass | Pass, 32 source/test files |
| Executor offline pytest | 202 passed; 5 network tests deselected | 350 passed; 5 network tests deselected |
| Engine counterexamples before fixes | 24 failed; 1 positive control passed; 3 later quote cases failed | 63 engine cases passed after repairs, including disk-failure, final-decision and token-index regressions |
| Journal counterexamples before fixes | 36 failed; 1 positive control passed | 41 dedicated integrity cases passed |
| Gate counterexamples before fixes | 35 failed; 1 positive control passed | 49 dedicated integrity cases passed |
| Failed-fee counterexamples before fixes | 20 failed; 2 positive controls passed | 22 dedicated cases passed |
| Backtester | Existing command discovered | 909 passed |
| Extension | Existing command discovered | 372 passed; offline closed round trip net $0.3492 |
| Docs and offline index | Existing commands discovered | Docs counts/drift passed; final offline index regeneration/check is a commit gate |

Required commands, run from `executor/`, are `.venv/bin/ruff check src tests`,
`.venv/bin/ruff format --check src tests` and `.venv/bin/pytest -q`. Cross-component gates
are the commands in `CLAUDE.md`. Final CI runs on the pushed head. The independent private-installed CLI check observes isolated
gate refusal and source identity; it does not claim production installation or venue acceptance.

The first backtester attempt inherited `INDEX_NO_AUTO=1` and failed eight mocked idle-index
assertions plus two dependent errors. The rerun used the suite's default environment and completed
all 909 tests with exit 0. The tests mock model/process starts; no indexing/model service started.

No live order, owner key read, service restart, actual research approval or user configuration
change was performed. Source tests and CI do not prove installed/live venue acceptance.

## 4. Activated review skills

`code-deep-optimizer` supplied scoped per-file correctness, adversarial, robustness,
concurrency and maintainability passes. `lang-python` supplied Python conventions;
`security-review` supplied trust-boundary and fail-closed checks. The baseline code-review
and coding-standards references informed review order. No held-out optimization evaluation
set was identified, so empirical promotion and a persistent champion were not used.

## 5. Diff scope

`journal.py`: validated replay and durable append. `gates.py`: validated persisted evidence,
serialized writers and durable state/audit writes. `engine.py`: late stop, ambiguity,
reconciliation lock/status and complete metadata evidence. The three new integrity suites
hold the counterexamples. README updates correct archived liquidity/manual-order descriptions
and document recovery behavior. The complete patch is the associated Git pull request. `ledger.py` also counts failed-chain fees;
`test_failed_fees.py` covers the measured-fee and unavailable-fee paths.

## 6. Independent final review

Two independent fresh-context reviewers inspected the primary final source and its immediate dependencies.
The first gate found two High and one Medium issue. Those repairs preceded the second gate, which found
one High and one Medium issue. All five gate findings received focused repairs and regressions. The two-gate
limit is reached, so the optimizer status remains **BLIND-AUDIT-DISSENT**. Passing regressions and an author
review do not replace a third independent gate. This is not repository-wide certification.

Independent private CLI acceptance bound its executable and editable module paths to this worktree.
All five isolated CLI invocations returned valid envelopes with exit 0. Missing, malformed and backwards-clock
research evidence kept live execution blocked, without modifying the evidence. A refreshed final acceptance
also verified pure-ledger failed-fee P&L of -$0.012345, no position creation and refusal of missing fees.
The verification process exited 0. Network was blocked. Final accepted source hashes:

| Source | SHA256 |
| --- | --- |
| `executor/src/executor/engine.py` | `4946188ba4930861bf442cc53c733545701ec78375821adec22ed2d30ef59c28` |
| `executor/src/executor/gates.py` | `4444f0efb3e92560a53725de5b1b9f62964711b1ac02b6e54e650a896c554f73` |
| `executor/src/executor/journal.py` | `3cbb4b970a2f3ca325fc1bf85cb85cf62614b2f9d8fe19e416ff60148f43478d` |
| `executor/src/executor/ledger.py` | `ef6d6613601c9254784ab7463f0a17106f7a2952d321061569d1135b8b774c93` |

## 7. Recommendations and boundaries

The recommendations implemented in this pass are the eighteen root-cause repairs above,
plus the corrected component descriptions and recovery guidance. These address defects
with reproducible triggers rather than adding strategies on uncertain evidence.

Existing work outside this pass remains separately recorded: authenticated Trigger fills,
fee attribution and its trusted intent verifier (`extension/README.md`); current-engine
regeneration of historical rankings (`README.md`); cross-chain execution and Jupiter API v2
adoption (`executor/CLAUDE.md`). They were not silently enabled. The owner's existing v1
choice and archived liquidity decision remain in force. This pass does not claim to implement
those independent workstreams or to demonstrate profitable trading.

## 8. Feature additions

No new trading behavior or command was added. All implemented changes enforce existing contracts.

## 9. Summary

3 iterations · 14 applicable file passes · scoped structural review · no known open repair · Verify: PASS · Status: BLIND-AUDIT-DISSENT.

All 18 reported root causes have focused repairs and passing regressions. The second independent
gate dissented before the last repairs; there is no third blind gate and no independent CLEAN claim.
Active file passes: C1-C3, S1-S5, P1-P2, M1-M2, M4, T1. T4 is N/A for the production
sources. Repo-wide M3/T2/T3/T4 were not a deep audit; existing CI/locked dependencies and
shared registries were inspected during orientation. Do not infer full repository coverage.

## 10. Snapshot and rollback

Pre-write snapshots are at
`/Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261108-executor-integrity/`.
For an authorized local rollback in the private worktree, the literal source restore commands are:

```bash
cp /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261108-executor-integrity/executor/src/executor/journal.py.iter1 /Users/mitch/dev/solmargintrader-wt-01a1be8d/executor/src/executor/journal.py
cp /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261108-executor-integrity/executor/src/executor/gates.py.iter1 /Users/mitch/dev/solmargintrader-wt-01a1be8d/executor/src/executor/gates.py
cp /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261108-executor-integrity/executor/src/executor/engine.py.iter1 /Users/mitch/dev/solmargintrader-wt-01a1be8d/executor/src/executor/engine.py
cp /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261108-executor-integrity/executor/src/executor/ledger.py.iter1 /Users/mitch/dev/solmargintrader-wt-01a1be8d/executor/src/executor/ledger.py
rm /Users/mitch/dev/solmargintrader-wt-01a1be8d/executor/tests/test_journal_integrity.py
rm /Users/mitch/dev/solmargintrader-wt-01a1be8d/executor/tests/test_gate_integrity.py
rm /Users/mitch/dev/solmargintrader-wt-01a1be8d/executor/tests/test_engine_integrity.py
rm /Users/mitch/dev/solmargintrader-wt-01a1be8d/executor/tests/test_failed_fees.py
rm /Users/mitch/dev/solmargintrader-wt-01a1be8d/docs/repository-review-2026-11-08.md
```

Regenerate offline indexes and run the gates again. The private worktree is removed after delivery;
these commands document the snapshot mapping for the original three suites plus the fee suite/report,
not a post-merge rollback procedure.
After merge, use a new reviewed revert PR; do not reset the shared checkout.

## 11. Index

Offline repository indexes are regenerated and checked before commit. Their final drift check is
a delivery gate. Semantic indexing and embeddings stay untouched.

## 12. Prior knowledge and continuation

Two memory-central lessons and ten conventions were consulted; current source verified the
unknown-submit and dry-run contracts. Prior PR35 scope limits informed this review. New
continuation context is in `memory.md`; Stele writes are queued because its MCP is unavailable.

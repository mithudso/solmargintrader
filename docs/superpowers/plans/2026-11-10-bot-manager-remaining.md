# Remaining Bot Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task by task. Preserve the existing execution method and accepted checkpoints. Steps use checkboxes for tracking.

**Goal:** Finish the standalone manager's research, accounting, monitoring, learning, browser integration and guarded executor integration, then provide Oracle with a verified interface and operating guide.

**Architecture:** Keep the manager's existing command registry, durable supervisor and per-bot journals. Delegate simulation, market history, research admission, browser control and signing to their established owners. Oracle and the graphical interface consume versioned manager state and command receipts.

**Tech stack:** Python 3.13+, SQLite, stdlib process control, existing NumPy/pandas simulation dependencies, existing JavaScript extension/native messaging and the existing executor. No new broker, recorder, signing service or UI framework is required by this plan.

**Spec:** /Users/mitch/dev/solmargintrader/docs/superpowers/specs/2026-11-09-bot-manager-design.md

**Approved milestone plan:** /Users/mitch/dev/solmargintrader/docs/superpowers/plans/2026-11-09-bot-manager.md

**Version:** 1.0.0

**Delta:** Initial remaining-work plan requested after the owner challenged repeated wrap-up claims.

**Snapshot:** 2026-11-10. Remote baseline inspected: `21331e37fe686558ddb16f720b986d664658184a`. This document distinguishes unfinished code, verification and elapsed evidence. It does not establish any new trading capability.

## Actual starting point

| Work | Verified state | What remains |
| --- | --- | --- |
| Milestones 1–2 | Delivered: specifications/defaults, owner-aware controls and independent persistent paper workers | Maintain compatibility; do not rebuild them |
| Bot editing | Delivered: immutable saved revisions, history/schema and explicit stopped adoption | Learning needs a separate account-preserving adoption boundary |
| Milestone 3 | Delivered in PR188, merge `a610868dbac61b46dba2a0047aa22d79b23cab34`: Grid, DCA, Trend and Momentum reference execution, prospective shared-source input and conditional cycle evidence | Current quotes/reference data do not certify Jupiter execution; prospective prefix currently has a 2,048-bar bound |
| Milestone 4, TASK-1110 | Source checkpoint committed on `agent-01a1c189-m4`; still unfinished as a release | Integrate current master, review, install, independently verify and deliver |
| Milestones 5–8, TASK-1111 through TASK-1114 | Not started | Tasks 2–7 below |
| Final Oracle handoff | Existing handoff covers earlier releases | Update and verify against the completed backend; Task 8 |

The accepted installed manager is 0.4.0 at /Users/mitch/.local/bin/solbot, backed by /Users/mitch/.venvs/solbot. Existing accepted ecosystem environments and active producers retain their own versions. The newer remote ecosystem package is 0.2.1; do not downgrade it to the M4 branch's earlier proposed 0.1.4.

Current implementation workspace: /Users/mitch/dev/solmargintrader-wt-01a1c189-editing

Current recovery ledger: /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/.superpowers/sdd/2026-11-09-bot-manager/progress.md

M4 checkpoint: source `e24ad7ca343a07910d04f3c3471494fcba763c75`, report/proof `65a5a40020a21849fadd3476c556a5d4cdedca3a`. The implementer reports 187 manager, 150 owner/legacy and 42 bridge tests passed, plus actual OS denial probes. These are source results awaiting independent review and installed acceptance. Report: /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/.superpowers/sdd/2026-11-09-bot-manager/task-m4-report.md

The primary checkout /Users/mitch/dev/solmargintrader is used by other live sessions. Do not switch its branch, stage its files or reset it to finish this work.

## Global constraints

- Defaults remain paper and disarmed. Saving a specification starts no worker, reserves no live capital and submits no order.
- Preserve distinct bot UUID, runtime ID, owner identity, generation and configuration revision/hash. Saving an edit never mutates an active run.
- Use the existing canonical algorithms. Grid ladder, DCA safety orders, buffered next-open Trend and time-series Momentum retain their exact semantics. Arbitrage remains conditional evidence unless verified execution exists. Council remains external-only initially.
- The manager uses one existing research authority. A new home, UUID, fingerprint or seed cannot reset attempts or reopen exposed dates.
- Missing price, amount, fee, mark or measurement remains unavailable with a reason. Never convert it to zero or guess a value that becomes an order.
- Process liveness, input quality, evaluation progress, evidence quality and submission certainty remain separate fields.
- Pause entries, stop owner, cancel orders, close positions and emergency kill/disarm are separate operations. Keep residual exposure and partial or unknown outcomes visible.
- Reconcile before planning. An ambiguous submit is never automatically retried. Preserve accepted request IDs and unresolved reservations across crashes.
- Reads do not initialize a database, start a producer, install a service, arm, optimize or adopt configuration.
- No new third-party runtime dependency unless an existing requirement cannot be met with the declared stack and the need is documented.
- Do not alter active immutable environments or another session's experiments to manufacture research coverage.
- Required checks must finish successfully. Every completed milestone reaches the remote default branch after final-head CI and independent installed acceptance where applicable.
- Keep /Users/mitch/dev/solmargintrader/prompts.md and /Users/mitch/dev/solmargintrader/memory.md versioned. Stage explicit task-owned files only.

## Review focus

1. **First use:** an owner can create, configure, run and research a bot with documented commands and defaults. No pasted Python identity or manually authored normal-use JSON is required. Task 1 owns the regression.
2. **Authority/history changes:** a new manager home, missing registered DB or disappearing source cannot reset evidence history or certify an unaware owner. Task 1 owns the public-process tests.
3. **Long-lived state:** crossing the current replay bound or restarting cannot reset grid geometry, DCA deals, indicators, lots, cash or pending next-open fills. Task 4 owns continuation parity.
4. **Partial control success:** slow/offline owners, stale generations and lost acknowledgements cannot become “all stopped” or repeated commands. Tasks 3 and 6 own per-bot receipt and offline tests.
5. **Financial uncertainty:** losing trades remain valid results; missing marks and unknown sends remain unresolved. Tasks 2, 5 and 7 own accounting, learning eligibility and reservation tests.

## File map

Paths below are canonical maintenance locations. Apply edits in the isolated implementation worktree until delivery.

| Action | File or module paths | Responsibility |
| --- | --- | --- |
| Finish/review | /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/research.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/research_owner.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/blind.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/blind_judge.py | M4 research orchestration, owner process and isolated deterministic judge |
| Finish/review | /Users/mitch/dev/solmargintrader/soltui/manager_evidence.py; /Users/mitch/dev/solmargintrader/soltui/research_owner.py; /Users/mitch/dev/solmargintrader/soltui/research_admission.py; /Users/mitch/dev/solmargintrader/soltui/experiments.py; /Users/mitch/dev/solmargintrader/soltui/experiment_runner.py | Canonical research admission, attempts, history and evidence receipts |
| Create | /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/accounting.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/reports.py | Pure accounting projections and bounded attributed reports |
| Create | /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/health.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/backup.py | Independent health dimensions, alert lifecycle and explicit backup/restore |
| Modify | /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/registry.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/status.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/store.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/ledger.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/supervisor.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/worker.py | Public commands, versioned state, durable events and existing worker supervision |
| Modify | /Users/mitch/dev/solmargintrader/oracle/quotes.py | Add a sequence-bearing bounded quote page without breaking existing list callers |
| Modify | /Users/mitch/dev/solmargintrader/backtester/core/engine.py; /Users/mitch/dev/solmargintrader/backtester/core/gridsim.py; /Users/mitch/dev/solmargintrader/backtester/core/dcasim.py; /Users/mitch/dev/solmargintrader/soltui/trend.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/strategies | Canonical resumable strategy state and bounded long-lived execution |
| Create | /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/learning.py | Labels, bounded proposals, actual prospective shadow gates and protected adoption |
| Modify | /Users/mitch/dev/solmargintrader/extension/src/core/commands.js; /Users/mitch/dev/solmargintrader/extension/src/bg/soltui-transport.js; /Users/mitch/dev/solmargintrader/soltui/native_host.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/adapters/extension.py | Browser-owned identity, delegated commands and durable acknowledgement bridge |
| Modify | /Users/mitch/dev/solmargintrader/executor/src/executor/registry.py; /Users/mitch/dev/solmargintrader/executor/src/executor/journal.py; /Users/mitch/dev/solmargintrader/executor/src/executor/gates.py; /Users/mitch/dev/solmargintrader/executor/src/executor/rails.py; /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/adapters/executor.py | Executor-owned wallet admission, reservations, replay safety and exact capability gates |
| Create/modify | /Users/mitch/dev/solmargintrader/botmanager/tests; /Users/mitch/dev/solmargintrader/soltui/tests; /Users/mitch/dev/solmargintrader/oracle/tests; /Users/mitch/dev/solmargintrader/backtester/tests; /Users/mitch/dev/solmargintrader/extension/test/bot-manager.test.js; /Users/mitch/dev/solmargintrader/executor/tests | Behavioral tests in the owner of each changed contract |
| Modify per release | /Users/mitch/dev/solmargintrader/botmanager/pyproject.toml; /Users/mitch/dev/solmargintrader/backtester/pyproject.toml; /Users/mitch/dev/solmargintrader/oracle/pyproject.toml; /Users/mitch/dev/solmargintrader/soltui/pyproject.toml; /Users/mitch/dev/solmargintrader/ecosystem/pyproject.toml; /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py | Compatible package versions, exact pins and immutable installed environments |
| Maintain | /Users/mitch/dev/solmargintrader/docs/bot-manager-handoff.md; /Users/mitch/dev/solmargintrader/docs/bot-manager-quickstart.md; /Users/mitch/dev/solmargintrader/docs/bot-manager-oracle-interface.md; /Users/mitch/dev/solmargintrader/.github/workflows/ci.yml | Operator access, client contract, installed acceptance and release checks |

## Ordered implementation tasks

### Task 1 — Finish and deliver M4 research

**Tracking:** TASK-1110. **Depends on:** delivered M3. **State:** source checkpoint complete; no independent M4 approval, installed acceptance or delivery yet. Checked source steps below are implementer-reported, not independent acceptance.

**Interfaces:** Existing manager registry owns `research-setup`, `research-plan`, `research-register`, `research-status`, `backtest` and `research`. The existing SolTUI registry owns `research.protocol`; the headless stdio module carries bounded bytes only. Command names being added in M4 remain unreleased until the registry/schema and installed tests agree.

- [x] Implement source fixes for strict client-descriptor and native-root admission: malformed known-client fields, disappearing previously observed history and a participating native process writing another local ledger all refuse. Unmanaged legacy behavior remains when participation is not configured.
- [x] Add source `research-setup` and `research-plan`: actual owner identity probe, descriptor creation without authority initialization, bounded neighboring unpinned search and the same default when `research` omits `--plan`. Public setup/default-plan source tests passed; installed end-to-end use is still pending below.
- [x] Add canonical registration and immutable owner-clock epoch. First initialization is explicit and limited to an unbound namespace. Source tests protect pre-epoch dates, allow verified post-epoch finals, ignore cutoff-reset attempts and retain the attempt ordinal. A missing registered DB refuses recreation.
- [ ] Verify scoped receipt validity: harmless later paper ticks retain a pending proposal; newly imported conflicting prior exposure or changed required participation makes it non-reconcilable. Stale proposal bodies remain inspectable. Temporary registry overrides are explicitly non-production.
- [ ] Preserve M4 statistical policy: freeze 50/25/25 chronology, horizon purge/embargo, objective and budget before evaluation; at most 32 configurations and 1,000 cells; at least 30 completed trades; drawdown at most 20%; score median(net return − 0.5 × drawdown), then lower turnover and incumbent retention. Freeze one challenger before final unseal. Require at least 10 independent decided blocks, positive median improvement and shared `alpha_k=0.05/(k*(k+1))`. Unsupported independence or uncertified current evidence returns a concrete refusal.
- [ ] Verify the actual macOS judge sandbox denies absolute resolver/repository reads and metadata access, network, fork and exec. Prove allowed startup as well as denial. Preserve the failed early Python startup probes. Unsupported hosts return `isolation_unavailable` and never run an unrestricted substitute.
- [x] Commit the M4 implementer's explicit files and report at the checkpoint hashes above.
- [ ] Integrate current master into the isolated branch, retaining PR189 control-room/Oracle changes and PR190's approved referral default. Recompute a forward compatible package matrix; do not release the obsolete ecosystem 0.1.4 plan over 0.2.1.
- [ ] Run all manager tests and affected owner/legacy suites. Use a fresh read-only task review for spec compliance and code quality. Resolve important findings before installation.
- [ ] Build fresh regular manager/ecosystem installations; independently run public setup, registration, backtest/research, owner subprocess and OS denial checks from outside the checkout. Compare installed production source/assets with reviewed source. Preserve the stopped default demo and actual research histories.
- [ ] Deliver through the release gate below, then mark M4 complete. Update the quickstart with the exact verified commands and actual unavailable-evidence reasons.

**Done means:** owner setup works through public commands, descriptive backtests work, conditional blind selection is isolated and evidence-bound, history cannot be reset, and the reviewed installed release is merged. It does not mean current incomplete Jupiter data has produced a certified profitable winner.

### Task 2 — Implement M5 accounting and useful reports

**Tracking:** TASK-1111. **Depends on:** Task 1's immutable run/evidence/receipt contract.

**Tests:** /Users/mitch/dev/solmargintrader/botmanager/tests/test_accounting.py; /Users/mitch/dev/solmargintrader/botmanager/tests/test_reports.py; /Users/mitch/dev/solmargintrader/oracle/tests/test_quotes.py.

**Interfaces:** Add pure `accounting_snapshot(run: Mapping[str, Any]) -> dict[str, Any]` in the accounting module and `report_page(store, bot_id: str, *, run_id: str | None, after: int, limit: int) -> dict[str, Any]` in the reports module. Public `report` supports human, JSON and CSV rendering from the same projection. Pages return stable sequence cursors and a bounded next cursor; row count is never a cursor.

- [ ] Write `test_fifo_partial_close_charges_each_fee_once`, `test_cashflow_identity`, `test_missing_mark_keeps_pnl_null` and `test_rent_is_not_profit`. Assert `equity = cash + marked_inventory` and `net_pnl = equity − starting_equity − deposits + withdrawals`. Use hand-calculated entry/exit fees, retained inventory, deposits/withdrawals and transaction expense; an unknown required component makes the affected total null with a reason.
- [ ] Implement exact Decimal arithmetic where the input is exact. Preserve reference simulator float lineage. Keep realized/unrealized, gross/net, costs, cash flows and unresolved residuals explicit. Separate backtest, reference paper, prospective paper and live; separate USD and USDC. Independent virtual accounts are not a funded wallet total.
- [ ] Add attributed reports and export for current/archived runs, configuration/provenance, source/timeframe, dataset/cost/engine identity, sample size, learning/selection status and loss cohorts. Compatible benchmarks may compare; incompatible ones return the mismatch.
- [ ] Add stable bounded pagination for events, reports and history. In the Oracle owner add a versioned quote-page result carrying each SQLite sequence plus `next_after`; preserve old list callers. Test ignored inserts/sequence gaps, append during paging and exact replay.
- [ ] Run accounting/report/quote tests, full manager tests and the affected Oracle tests. Check old run attribution and no database mutation during reads. Commit explicit owned paths for review with Task 3.

**Done means:** a user can see where profit/loss came from, what costs are included and what is unknown, in all three formats, without loading an unbounded archive or double-counting capital/fees.

### Task 3 — Implement M5 health, alerts, pause semantics and recovery

**Tracking:** TASK-1111. **Depends on:** Task 2 accounting projection and existing supervisor.

**Tests:** /Users/mitch/dev/solmargintrader/botmanager/tests/test_health.py; /Users/mitch/dev/solmargintrader/botmanager/tests/test_backup.py; /Users/mitch/dev/solmargintrader/botmanager/tests/test_supervisor.py.

**Interfaces:** Add `health_snapshot(runtime: Mapping[str, Any], *, now: float) -> dict[str, Any]`. Integrate periodic checks into the existing supervisor. Add registry-backed alert inspection and explicit backup/restore; reuse the existing status, control and durable event envelopes. Implement `pause`/`resume` only for strategy models that can distinguish new entries from existing exits.

- [ ] Write `test_alive_process_can_have_stale_inputs`, `test_stopped_bot_retains_exposure`, `test_alert_dedup_and_resolution` and `test_restore_preserves_research_authority`. Cover fresh data/stalled evaluation, unreachable owner, valid losing result and failed measurement as independent states. Assert `status --why` includes the latest completed evaluation/decision, reason, blockers and next trigger.
- [ ] Implement persistent deduplicated alerts with cooldown, resolution evidence and bot/run/source attribution. Performance warnings require a compatible baseline and enough observations; absent evidence is unavailable, not healthy or a zero-loss result.
- [ ] Test and implement pause-entry semantics. New entries stop while ownership/exposure remains visible and existing exits follow the declared strategy model. Unsupported models report the exact capability reason. Stop is never relabelled as pause; cancellation and closing stay separate.
- [ ] Implement SQLite backup with manifests/checksums and capture cutoffs. Include specifications, run archives, request receipts, immutable evidence references and canonical research registration bindings. Restore only to a new selected home, start nothing, and never overwrite/roll back the live research authority or reopen spent dates. Test corruption, missing dependencies and uncertain ownership.
- [ ] Bound diagnostic log rotation while retaining referenced financial/training evidence. Verify restore and report identities against the copied ledger.
- [ ] Run the documented 10-paper-bot plus one-optimizer fault/load fixture with the default four-worker pool. Report four active and six queued where applicable. Measure status p95 <1 second, durable stop acknowledgement <2 seconds, owner release ≤10 seconds and crash/stall detection ≤15 seconds. Verify forced restart produces no duplicate fills/events. Fix a missed SLO or publish its measured limitation.
- [ ] Run full manager and changed owner tests, review Tasks 2–3, verify actual installed report/backup/health behavior and deliver M5 through the release gate.

**Done means:** status explains behavior, failures produce attributable alerts, controls retain exposure and the copied state restores safely. Capacity claims match measured worker counts and timings.

### Task 4 — Remove the M6 long-lived runtime blocker

**Tracking:** TASK-1112. **Depends on:** M5 accounting/recovery.

**Tests:** /Users/mitch/dev/solmargintrader/botmanager/tests/test_continuation.py and the changed canonical owner's tests under /Users/mitch/dev/solmargintrader/backtester/tests.

**Interfaces:** Extend canonical strategy owners with versioned resumable state consumed by the existing manager strategy dispatcher. Each checkpoint binds prior-segment digest, active config/engine/source identities, observation cursor, cash, lots and pending action. Archive immutable completed segments; do not create a parallel engine or supervisor.

- [ ] Write `test_segmented_restart_matches_uninterrupted_after_2048_bars` for Grid, DCA, Trend and Momentum. Assert decisions, fill timing, lots, cash, fees, realized/unrealized P&L and starting-capital attribution agree across more than 2,048 closed bars.
- [ ] Implement bounded continuation in the canonical owners: fixed grid ladder geometry, DCA deal/safety-order state, Trend/Momentum warmup and hysteresis, and pending next-open targets all survive a boundary. Bound memory and checkpoint growth without deleting attributed financial evidence.
- [ ] Test crash before/after segment transition, duplicate source observations, stale config and missing prior segment. Continue atomically or refuse with a recoverable reason. Never silently change timeframe or reset indicator/account history to meet the resource bound.
- [ ] Run full manager tests and affected canonical economic/parity tests. Review and independently verify installed continuation. Bump changed first-party package versions and compatible pins together. Deliver this independently useful prerequisite before enabling automatic learning.

**Done means:** supported one-minute paper bots can collect genuine seven-day evidence without hitting the old prefix limit, and a restart preserves the same economic account. Unsupported family limits remain explicit.

### Task 5 — Implement M6 labels, shadow evaluation and protected learning

**Tracking:** TASK-1112. **Depends on:** Tasks 1–4.

**Tests:** /Users/mitch/dev/solmargintrader/botmanager/tests/test_learning.py and publication/receipt tests under /Users/mitch/dev/solmargintrader/soltui/tests.

**Interfaces:** Learning consumes attributed resolved outcomes, M4 evidence-bound proposals and M5 health/accounting. Add registry-backed proposal creation/inspection, promotion and rollback through the existing owner protocol. A proposal records current/proposed values, originating revision/hash, pins, evidence identity, counts, shadow clocks and adoption state. Owner and manager DBs use durable idempotent reconciliation, not a claimed cross-DB atomic transaction.

- [ ] Write `test_learning_uses_all_eligible_outcomes`, `test_normal_loss_does_not_mutate_config`, `test_day7_and_trade30_are_both_required`, `test_pins_and_cas_retain_incumbent` and `test_adoption_crash_reconciles_once`. Cover incorrect resolved forecast, completed net-loss trade, execution fault, data fault and unresolved inventory. Report loss cohorts separately.
- [ ] Implement daily bounded proposals after at least 300 resolved comparable labels AND 30 completed trades, at most one proposal per canonical scope/day and a 48-hour promotion cooldown. Reuse M4 admission, attempts and optimizer ownership. A new bot name/UUID/seed cannot reset them.
- [ ] Preserve manual pins and immutable provenance. Exclude risk limits, capital increases, operating mode and global strategy defaults from automatic tuning. Publish compatible learned defaults through the owner protocol, not direct file overwrite.
- [ ] Test day 7 AND completed trade 30 boundaries. Require certified compatible evidence, isolated blind selection, fresh-final acceptance, at least seven actual calendar days of prospective shadow operation, at least 30 comparable completed shadow trades, healthy reconciliation, unchanged originating revision/pins, cooldown and risk compatibility. Reject forged client clocks and historical replay labelled prospective.
- [ ] Implement account-preserving promotion at a supported safe boundary. Carry cash, inventory, outstanding intents and economic history; bind each new segment to its predecessor. If flat state is required, wait explicitly. Never use independent-run reset to discard losses or count initial capital again.
- [ ] Implement evidence-bound request dedup/CAS and crash recovery around owner receipt and manager revision publication. A failed gate retains the incumbent. Rollback stages a verified compatible prior revision through the same safe boundary; it cannot undo trades or remove unknown sends.
- [ ] Run label/learning/continuation/owner-publication tests and full manager tests. Review and verify installed pending/eligible/rejected transitions. Deliver M6 code; separately report actual production shadow gates still pending.

**Done means:** learning proposals, explanation, inspection and guarded transitions work. Code acceptance with fixture clocks does not establish that a real bot has already completed seven days or 30 trades.

### Task 6 — Implement M7 browser discovery and delegated controls

**Tracking:** TASK-1113. **Depends on:** delivered manager status/control/receipt contracts.

**Tests:** /Users/mitch/dev/solmargintrader/extension/test/bot-manager.test.js; /Users/mitch/dev/solmargintrader/botmanager/tests/test_extension_adapter.py; native-host tests under /Users/mitch/dev/solmargintrader/soltui/tests.

**Interfaces:** The actual extension registry owns browser actions; native messaging carries strict versioned envelopes. Bind `(source, installation_id, native_id)` to a stable manager reference. Control receipts bind request ID, bot identity, owner/config generation, operation and outcome. Browser state is read through its owner, never by opening Chrome's databases.

- [ ] Write tests for stable real-browser installation identity, multiple profiles, hostile/unknown fields, origin spoofing, stale config/generation, duplicate or transplanted requests, expired/offline owner and secret-canary exclusion.
- [ ] Add extension-initiated registration and bounded polling using MV3 startup/alarm behavior. Maintain the existing one global browser grid slot and legacy SolTUI family slots; per-coin settings do not create independent workers.
- [ ] Implement write-ahead request receipt/reconciliation across browser storage and manager/native state. Lost acknowledgement may resend the same receipt; it must never repeat an ambiguous owner control. Later stop revokes earlier queued starts. Preserve pending, acknowledged, failed, skipped and unknown outcomes separately.
- [ ] Keep delegation when both owners cannot provide durable prepare/quiesce/snapshot/commit and generation fencing. Advertise transfer unavailable with its reason; a new manager lock cannot seize an unaware running owner.
- [ ] Add a separate isolated-paper Chrome acceptance gate for manager start/stop and native registration. Preserve the ordinary e2e disarmed guard. Verify loaded extension version/source, actual browser storage, native origin and offline behavior in a test-owned profile; do not overwrite the user's profile or native manifest.
- [ ] Run extension unit/parity/e2e/offline economics plus changed native-host and manager tests. Bump extension manifest/package together, review, independently verify loaded behavior and deliver M7. State whether the user's everyday browser installation has actually been updated.

**Done means:** the manager discovers and controls the real browser-owned supported paper bot with attributable receipts and honest offline state. It does not claim unsupported multi-instance browser execution or ownership transfer.

### Task 7 — Implement M8 guarded executor integration

**Tracking:** TASK-1114. **Depends on:** exact research/shadow/config identity and existing executor verifier/journal.

**Tests:** /Users/mitch/dev/solmargintrader/botmanager/tests/test_executor_adapter.py and reservation, journal, rails and surface tests under /Users/mitch/dev/solmargintrader/executor/tests.

**Interfaces:** Existing executor registry owns versioned capabilities, admission, reservation, intent and reconciliation. The manager adapter delegates; it never signs. Evidence scope binds strategy/version, config hash, mints, timeframe, execution/cost/data model, installed owner and research/shadow receipts. Aggregate risk scope is canonical strategy plus wallet, independent of bot UUID.

- [ ] Re-read /Users/mitch/dev/solmargintrader/executor/CLAUDE.md. Keep owner-selected Jupiter Swap v1. Trigger/V2 and non-atomic multi-leg arbitrage remain unsupported without their separate independent verifiers/construction. Preserve stricter path-validation restrictions.
- [ ] Test and implement a shared wallet writer plus atomic executor-owned reservations across supported clients/homes. Require an explicit shared-wallet portfolio cap; subtract observed pending spends, fees and reserves. Known unaware writers prevent sole-owner admission.
- [ ] Aggregate position/trade/daily-loss limits across instances and config revisions. Existing defaults include $25 maximum position, $10 maximum trade and $10 daily loss per strategy; never increase configured limits through a new bot name or paper balance.
- [ ] Persist exact caller intent/request binding before possible signing. Identical replay returns the original receipt, mismatched context conflicts, and a crash or timeout after send remains unknown. Retain its reservation until proven no-send or reconciled terminal evidence. One application send only.
- [ ] Require exact current compatible research/shadow evidence, healthy input/accounting, owner/installed identity, wallet budget, verifier, kill/loss/risk gates and no unresolved sends for entries. Missing price/size/fee/decimals/marks refuses. Keep legitimate tracked reduce-only recovery under existing exit semantics and verifier limits.
- [ ] Keep executor average-cost risk accounting distinct from the manager's FIFO reporting projection; reconcile confirmed atomic deltas/fees explicitly.
- [ ] Run the executor's offline pytest/Ruff/format suites plus manager/changed owner tests. Review malicious transaction, concurrent wallet, replay/transplant and crash/reconciliation cases. Independently verify installed keyless/dry-run admission and explicit refusal paths.
- [ ] Deliver guarded integration code through the release gate. Report actual venue/data/soak/signing certification separately. Do not perform a real-money test or advertise autonomous live readiness to make this checkbox pass.

**Done means:** the integration enforces real shared authority, budget and replay gates, with independently verified installed dry-run behavior. Actual live activation remains blocked wherever required real evidence is absent.

### Task 8 — Complete the Oracle interface and final acceptance

**Tracking:** implementation epic EPIC-1106, coordinated with the existing Oracle interface task TASK-1154. **Depends on:** delivered backend tasks above.

**Interfaces:** The visual client consumes manager registry/schema, bounded snapshots/history/reports and command receipts. Preserve current ecosystem control-room behavior; expose manager-owned controls through it as a client rather than adding another supervisor, optimizer, recorder, signer or strategy implementation.

- [ ] Update /Users/mitch/dev/solmargintrader/docs/bot-manager-handoff.md with features, access, exact defaults, maintenance owners, schemas/state locations, backup/restore, troubleshooting, verification receipts and remaining real-data gates.
- [ ] Execute every normal first-use example in /Users/mitch/dev/solmargintrader/docs/bot-manager-quickstart.md from a fresh isolated home. Verify bare CLI/help, create, inspect, edit, prepare input, paper start, daemon ownership, status explanation, stop, research setup and report. No guessed numbers or manually built normal-use descriptors.
- [ ] Update /Users/mitch/dev/solmargintrader/docs/bot-manager-oracle-interface.md with actual versioned fields, pagination, units/null reasons, lifecycle/input/evidence/submission dimensions, capabilities and per-bot outcomes. Include representative success, pending, partial, unavailable and unknown receipts with secret-free fixtures.
- [ ] Preserve UI semantics from the approved design: fleet roster and selected-bot inspector, persistent blockers and attributable activity, explicit draft/preparation/backtest/prospective/live stages. A draft creates no worker and reserves no capital. A button never supplies backend authority.
- [ ] Perform one final cross-milestone integration review. Verify migrations, archived attribution, continuous runtime/accounting, research-to-learning receipt identity, external owner controls, wallet admission and installed-source identity together. Fix concrete findings in their owner modules.
- [ ] Run final relevant source checks and independent installed end-to-end acceptance. Verify no test-owned process/lock/service remains and the original stopped demo, old immutable environments and other sessions' files are preserved.
- [ ] Deliver final docs/integration changes, report the completed backend contract to the Oracle task, and close only genuinely completed tracker work. Record real pending evidence/time/owner limitations explicitly; do not mark a capability ready from a fixture or an unmerged branch.

**Done means:** the owner can use and maintain the CLI, and Oracle can implement the visual client without guessing execution authority or redefining financial/state semantics.

## Verification commands

Run from the active isolated implementation workspace. Commands below are developer checks, not steps the owner must execute to use a bot. Source-path overrides are deliberate for source tests; installed acceptance uses `-I`, no `PYTHONPATH`, and a directory outside the checkout.

```bash
cd /Users/mitch/dev/solmargintrader-wt-01a1c189-editing
PYTHONPATH=/Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src:/Users/mitch/dev/solmargintrader-wt-01a1c189-editing /Users/mitch/.venvs/solbot/bin/python -m unittest discover -s /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/tests -t /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager -v
```

For M4 owner/legacy regressions, run the changed owner suites and the complete existing experiments/runner suites in the headless dependency environment. For canonical changes, run the full backtester suite and changed pure Trend tests. Expected result: completed exit code 0, with no newly unexplained warnings or lost legacy behavior.

```bash
cd /Users/mitch/dev/solmargintrader-wt-01a1c189-editing
PYTHONPATH=/Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src:/Users/mitch/dev/solmargintrader-wt-01a1c189-editing /Users/mitch/.venvs/solbot/bin/python -m unittest soltui.tests.test_experiments soltui.tests.test_experiment_runner -v
/Users/mitch/.venvs/solbot/bin/python -m unittest discover -s /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/backtester/tests -t /Users/mitch/dev/solmargintrader-wt-01a1c189-editing -v
```

For M7, use the extension's existing unit and real-browser gates. Expected result: unit/parity/economics and both ordinary and separate paper-control browser gates pass; no real order capability is enabled.

```bash
npm --prefix /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/extension test
npm --prefix /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/extension run e2e
```

For M8, use the existing executor's own declared environment. Resolve the physical environment path from the active installation if the worktree does not contain its own venv; do not invent a new install or use a UI interpreter. The accepted existing path below is outside the implementation worktree. Set pytest's target to the reviewed worktree code/tests when validating a candidate.

```bash
cd /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/executor
/Users/mitch/dev/solmargintrader/executor/.venv/bin/ruff check src tests
/Users/mitch/dev/solmargintrader/executor/.venv/bin/ruff format --check src tests
PYTHONPATH=/Users/mitch/dev/solmargintrader-wt-01a1c189-editing/executor/src /Users/mitch/dev/solmargintrader/executor/.venv/bin/pytest -q
```

Use required root documentation and offline-index gates after explicit new paths are staged and all Git conflicts are resolved:

```bash
cd /Users/mitch/dev/solmargintrader-wt-01a1c189-editing
python3 index/build.py all
python3 index/build.py --check
PYTHONPATH=/Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src:/Users/mitch/dev/solmargintrader-wt-01a1c189-editing /Users/mitch/.venvs/soltui/bin/python scripts/check_docs.py
git diff --check
```

The offline index commands do not authorize semantic regeneration, inference or embeddings. The docs gate counts committed tests, so run it against the committed candidate rather than lowering documented counts to hide a missing import or staged-only test.

## Release gate for every completed milestone

1. Freeze the named scope and record exact source/test results. A changing implementation is reported as implementation, never wrap-up.
2. Commit explicit owned files and obtain independent spec/quality review. Important findings reopen implementation; rerun affected checks after fixes.
3. Install a fresh regular candidate and compare loaded source/assets. Independently exercise the requested public behavior outside the checkout, preserving production state.
4. Update package pins, operator/client docs, prompt/continuation records and offline indexes. Push a recoverable draft checkpoint if work must continue; label it unfinished.
5. Push the final reviewed branch tip, obtain passing required CI on that exact head, then merge last. Verify merged content on remote master. A successful earlier CI run or a queued merge is insufficient.
6. Clean only this task's merged branch/worktree. Preserve the active plan workspace until the entire implementation is finished. Complete the milestone tracker after actual delivery.

No new routine approval is required: the owner already approved implementation and delivery. A real credential, denied operation, destructive action or missing external prerequisite is reported precisely instead of being concealed as progress.

## Critical path and elapsed evidence

**Implementation order:** finish M4 → M5 accounting/health → M6 continuation → M6 learning → M7 browser → M8 executor → final Oracle integration/handoff. Independent code prerequisite releases within M5/M6 may ship separately while preserving that dependency order.

**Engineering completion** requires working code, review, installed behavior, final-head CI and delivery. Several substantial subsystems remain; there is no verified hour estimate. Record measured gate progress rather than another short wrap-up estimate.

**Evidence readiness** additionally requires real compatible source data, full required owner participation, certified cost/fill models, untouched final windows, sufficient samples and actual prospective shadow time. The learning gate is at least seven calendar days AND 30 completed comparable shadow trades; either may take longer. Fixture clocks and historical replay do not satisfy it.

**Live readiness** additionally requires the exact executor/venue/verifier, shared-wallet admission, reconciled intents and the existing live policy. Implementing the checks does not create missing route history, fill evidence, profitable results or a completed soak.

Do not block useful reports, controls, continuation, browser integration or guard implementation merely because production evidence is still accumulating. Do not waive an evidence gate to claim all milestones are live-ready.

## Scope boundaries and decisions retained

- The future visual interface belongs to Oracle's integration work. This plan supplies its backend contract and examples; it does not start another graphical rewrite.
- Spot, long-or-flat, Solana/Jupiter and the verified mint allowlist remain. No Base liquidity reactivation, perps, shorts or silent venue migration.
- Use owner-selected Swap v1. The older Trigger-oriented venue memory does not override /Users/mitch/dev/solmargintrader/executor/CLAUDE.md or the approved standalone manager design.
- Scoped research freshness follows the canonical managed authority and verified required owners (KNOW-1216). It never claims every undisclosed process on the machine is absent, and it never treats a known unaware client as fenced by declaration.
- Preserve the newer ecosystem 0.2.1 control room, its existing producer ownership and approved 50bps manual referral behavior when integrating M4 (KNOW-1221). Those changes do not certify manager execution fees or a profitable edge.
- Saving a new config, automatic paper adoption and live activation remain separate receipt-backed operations. A UI client cannot collapse them.

## Plan self-review

- [x] Cover every unfinished approved milestone and the requested Oracle handoff.
- [x] Preserve completed M1–3/editing checkpoints and identify M4 as unfinished.
- [x] Give each task an owner boundary, affected files, dependency, observable tests and done criterion.
- [x] Include setup usability, current-master integration, bounded continuation, financial uncertainty, scope/pin/CAS protection and actual browser/wallet authority.
- [x] Separate engineering acceptance, required elapsed evidence and live readiness.
- [x] Keep execution in an isolated worktree and preserve existing package/producer/owner state.

Plan delivery tracking: TASK-1220. Implementation epic EPIC-1106 remains open until its actual required work is complete.

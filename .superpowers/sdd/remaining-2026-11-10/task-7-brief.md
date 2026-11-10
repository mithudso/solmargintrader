# Global constraints

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

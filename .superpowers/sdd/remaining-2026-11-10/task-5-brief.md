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

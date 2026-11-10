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


### Task 4 — Remove the M6 long-lived runtime blocker

**Tracking:** TASK-1112. **Depends on:** M5 accounting/recovery.

**Tests:** /Users/mitch/dev/solmargintrader/botmanager/tests/test_continuation.py and the changed canonical owner's tests under /Users/mitch/dev/solmargintrader/backtester/tests.

**Interfaces:** Extend canonical strategy owners with versioned resumable state consumed by the existing manager strategy dispatcher. Each checkpoint binds prior-segment digest, active config/engine/source identities, observation cursor, cash, lots and pending action. Archive immutable completed segments; do not create a parallel engine or supervisor.

- [ ] Write `test_segmented_restart_matches_uninterrupted_after_2048_bars` for Grid, DCA, Trend and Momentum. Assert decisions, fill timing, lots, cash, fees, realized/unrealized P&L and starting-capital attribution agree across more than 2,048 closed bars.
- [ ] Implement bounded continuation in the canonical owners: fixed grid ladder geometry, DCA deal/safety-order state, Trend/Momentum warmup and hysteresis, and pending next-open targets all survive a boundary. Bound memory and checkpoint growth without deleting attributed financial evidence.
- [ ] Test crash before/after segment transition, duplicate source observations, stale config and missing prior segment. Continue atomically or refuse with a recoverable reason. Never silently change timeframe or reset indicator/account history to meet the resource bound.
- [ ] Run full manager tests and affected canonical economic/parity tests. Review and independently verify installed continuation. Bump changed first-party package versions and compatible pins together. Deliver this independently useful prerequisite before enabling automatic learning.

**Done means:** supported one-minute paper bots can collect genuine seven-day evidence without hitting the old prefix limit, and a restart preserves the same economic account. Unsupported family limits remain explicit.

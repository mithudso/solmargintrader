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

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

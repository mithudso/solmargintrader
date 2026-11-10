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

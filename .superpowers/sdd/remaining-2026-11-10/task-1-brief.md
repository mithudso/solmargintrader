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

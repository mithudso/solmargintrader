# Task 7 — M8 guarded executor integration

Version: 1.0.2
Delta: 1.0.1 -> 1.0.2; bound pending enrollment writer awareness after independent crash-replay review. Previous delta: 1.0.0 -> 1.0.1; repaired all four independent-review findings. Initial implementation: implemented shared executor wallet authority, exact caller intents and guarded optional manager delegation; executor 0.1.0 -> 0.2.0 with synchronized uv.lock.

## Implemented

The executor owns one authority per OS user and wallet. Its path uses pwd.getpwuid(os.getuid()).pw_dir, independent of EXECUTOR_HOME, HOME, bot UUID or manager home. wallet.register requires an explicit portfolio cap and complete known-writer inventory. It retains existing clients, imports legacy journal history before admission and blocks known unaware writers. A previously existing default executor home is discovered conservatively. Missing registered ledgers/policies and truncated shared history refuse recreation/reset. Shared journal anchors preserve the already-observed prefix.

Every supported live swap takes the shared wallet writer lock, uses the shared executor journal and applies sticky conservative risk limits. Canonical risk families aggregate positions and daily realized loss/fees across homes, bots and configuration revisions. New entry labels outside canonical families refuse. Unclassified legacy open risk/loss blocks new canonical entries. The explicit wallet portfolio cap deducts open cost/independent marked value, pending spends, measured transaction fees and the native reserve. Missing balances, fee measurements, prices, decimals or marks refuse. Cross-home KILL files stop entries. Existing tracked reduce-only exit semantics and the stricter path-validation code caps remain intact.

Before possible signing, SQLite persists a canonical caller UUID and exact normalized intent, owner/source/config identity and optional manager scope. Identical replay returns its existing receipt; changed context conflicts. Reservations persist before signing. The existing verified Swap v1 send pipeline remains the sole signer/sender. A crash or ambiguous send retains its reservation and never retries. Explicit executor reconciliation releases a reservation only after terminal chain evidence, or after the shared writer proves no sending journal existed. Signing and sending do not occur in manager code.

manager.admit and manager.swap require exact strategy/version, config hash/revision, bot/runtime/generation, mints, timeframe, pinned strategy execution model, measured data/cost model and reviewed installed executor identity. Certificate reads are bounded. Both research and shadow receipt bytes must exist in executor-owned storage, match their digests and bind the exact scope with certified production eligibility. A digest or caller boolean alone is insufficient. Admission repeats before signing and immediately before send, including after the sending journal write. Source/config/installation drift, stale or revoked evidence and unhealthy accounting/input refuse.

Current reference-only M4 evidence has no production certificate issuer. This release adds no command to manufacture certification. Missing or incompatible evidence remains an explicit activation blocker. Initial manager entries support versioned Trend/Momentum next_open intents through the verified atomic Jupiter Swap v1 pipeline. Grid/DCA Trigger/safety ladders, Swap V2, Trigger and non-atomic arbitrage entries remain unsupported. Legitimate tracked Grid/DCA reduce-only exits retain existing executor verification and exit gates.

## Public interfaces

Executor registry owns wallet.capabilities, wallet.register, manager.admit, manager.swap and manager.status. Existing swap accepts an optional durable request_id; existing reconcile operates on the shared authority. CLI/API transport remains registry-owned; no signing logic was added to surfaces. Read-only context loading no longer creates a missing configuration file.

Manager executor_commands.command_specs exports executor-setup, executor-capabilities, executor-admit, executor-intent, executor-status and executor-reconcile. The controller owns their root registry integration. executor-setup probes a selected regular installed interpreter using -I -B, then writes an immutable reviewed descriptor through write_document. It initializes no wallet authority, arms nothing and loads no keys. The adapter strips PYTHONPATH, bounds process output/deadline, sanitizes owner failures and never retries an unknown send. Executor dependencies remain optional to manager users.

## Verification

- Full executor offline pytest: 474 passed, 5 network tests deselected, final exit 0 before the final execution-model clarification/version bump.
- Final affected authority/manager-admission suite after clarification: 46 passed, exit 0. Includes tracked Grid exit despite KILL without a certificate; unsupported entry construction remains refused.
- Final executor Ruff check: exit 0; Ruff format --check: 37 files already formatted, exit 0.
- Manager adapter/setup tests: 7 passed, exit 0; changed manager modules/tests Ruff clean.
- uv lock synchronized only executor version 0.1.0 -> 0.2.0; no runtime dependency added.
- Source diff whitespace check passed.

Tests cover concurrent cross-home writer exclusion, canonical aggregate position/daily-loss limits, explicit cap and fee/reserve accounting, unaware writers, missing-ledger/policy reset attempts, shared journal deletion, UUID replay/transplant, crash before signing, crash during application send, reservation reconciliation, reference/unsupported models, missing or fabricated receipt artifacts, certificate expiry/health and revocation after journaling, keyless refusal, actual synthetic dry-run verification, synthetic one-send execution and legacy tracked exit exemptions. Existing malicious transaction/verifier/journal/surface suites passed in the full offline run.

The original executor .venv is absent. The controller authorized a dedicated verification-only environment at /Users/mitch/.local/state/solbot/releases/0.5.0/executor-test-venv. It contains an editable test installation, not installed acceptance. No production environment, authority, actual research history or real key was loaded or changed. No network/live-money test ran. Test signing uses synthetic existing fixtures only. No new runtime dependency was introduced.

## Remaining controller gates and limitations

Perform fresh independent source review, final integrated tests and regular installed outside-checkout acceptance with exact source/asset parity. Include executor 0.2.0 in the regular candidate installation; the editable test environment is not that proof. Verify public executor-setup/capabilities and keyless refusal through the installed manager registry. Real production activation remains blocked without independently certified compatible research/shadow evidence, actual venue/data/soak evidence, explicit wallet enrollment and live configuration/call flags. No autonomous live-readiness claim is established by this source work.

## Independent review remediation — all four findings

The independent review found three P1 gaps and one P2 gap. This correction supersedes earlier statements that manager-originated live fixtures established an available live delegation path. Current manager specifications remain paper/disarmed virtual accounts. The manager and executor now explicitly refuse all manager-originated live requests because no independently verifiable manager live authorization implementation exists. A compatible certificate or live request flag cannot override that refusal. Existing direct executor tracked --exit recovery still follows the original tracked-quantity, unknown-send, verifier and fee/reserve rules; its dedicated regression passes despite KILL. No certificate issuer was introduced.

1. **Imported history:** enrollment writes a durable enrollment.pending marker before import. The marker binds the exact known-client histories, portfolio cap and observed risk ceilings. Enrollment imports idempotently, persists the journal anchor, then publishes policy and clears the marker with directory synchronization. Successful first and additional enrollment therefore cannot have a zero-length anchor over imported sending history. Interrupted enrollment blocks ordinary checks/admission. Exact replay retains the same uncertainty and refuses changed history. Tests delete only the shared journal after first/additional import, interrupt before anchoring and after anchored import, replay enrollment and verify unknown barriers survive or refuse.

2. **Tighter ceilings:** authority observations read the three configured risk ceilings from all known existing client configuration files, retain every previously observed lower ceiling and record client/shared policy revisions. effective_config persists newly observed lower limits under the shared wallet lock; a different thread/home cannot race enrollment over that observation. New enrollment also reads existing clients' tighter files. Pure checks/admissions/dry-run use the conservative observed projection without writing. Capabilities remain inert. Tests reproduce tightening A without re-enrollment, then enrolling B with defaults, for position/trade/daily loss; each stays at the lower ceiling. Concurrent same-object and second-home writer attempts refuse and leave lock ownership intact.

3. **Manager authorization:** manager executor_commands reads actual pinned mode/arming, runtime desired/observed state, process/input/evaluation health, accounting scope, entry pause and generation. Preview scope now contains an exact authorization object with mode, armed, desired, observed, input_state, accounting_state and entries_paused. Client-supplied authorization claims must match actual state. Paper/disarmed live requests never reach owner transport, including transplanted exit flags. Ineligible or hypothetical live runtime states also refuse; the current paper-only model never delegates live. The executor independently checks authorization shape/mode/state and refuses even eligible-looking forged client claims because its manager live authorization issuer is unavailable. Synthetic certificates do not bypass this gate. Raw executor manual recovery remains available under existing restrictions.

4. **Dry-run parity:** dry-run takes the shared writer for a stable read, evaluates shared journal/effective aggregate rails and the same measured portfolio budget, and uses reserve=False. It binds no request, reserves no capital, persists no risk policy edit and initializes no absent authority. Over-cap or unavailable financial evidence refuses before soak credit. Unresolved wallet requests/sends produce would_send=False with an explicit blocker and no soak credit. Paired $1 dry-run/live tests against a $1.40 cap both refuse once measured fees/reserve are included; the dry-run leaves request count, policy bytes and soak unchanged. Known tighter client limits also refuse during dry-run without persistence.

Completed final checks for this correction:

- /Users/mitch/.local/state/solbot/releases/0.5.0/executor-test-venv/bin/pytest -q from the worktree executor directory: **488 passed, 5 network tests deselected**, final exit 0.
- The same environment's Ruff check over src/tests: exit 0. Ruff format --check: **37 files already formatted**, exit 0.
- Manager tests.test_executor_adapter with worktree absolute PYTHONPATH: **11 tests passed**, final exit 0. This includes the actual _request boundary reproduction, scope/arming and generation transplants, lifecycle/reference-health refusals and inert setup transport.
- Ruff check/format --check over the manager adapter, executor command module and adapter tests: exit 0; three files formatted. Owned-path git diff --check: exit 0.

Only source and synthetic temporary test state changed. No real key, network, production wallet home or installed candidate was used. Independent re-review, final regular installed acceptance and delivery remain controller gates.

## Remaining independent P1 — pending writer awareness

The reviewer reproduced first and additional enrollment crashes before policy publication where replay kept the same wallet, cap, roots and history digests but changed a newly observed writer from aware=False to aware=True. The pending record did not bind awareness. This could remove the known-unaware writer barrier before policy publication.

The pending record now includes the exact normalized writers map from absolute root to strict awareness boolean. Replay compares that map with the retained record before imports or policy publication. A changed awareness flag refuses and leaves the pending marker unchanged. Pending records from the earlier schema without this map fail closed; the code does not guess their original awareness. Unchanged replay remains supported and retains the original unaware-writer admission block.

Regressions exercise both first enrollment and additional-client enrollment with a real RuntimeError injected only at policy publication. Each verifies false-to-true replay refusal, unchanged pending bytes, successful exact original replay and continued unaware-writer refusal afterward. A separate regression removes the map to simulate an older pending record and confirms both replay and admission refuse. All state uses synthetic temporary authorities; no key, network, production home or candidate installation was accessed.

Completed checks: targeted authority suite **62 passed**, exit 0; full offline executor pytest **491 passed, 5 network tests deselected**, exit 0; executor Ruff check exit 0; Ruff format --check **37 files already formatted**, exit 0. Changes are staged for the controller's in-progress integration merge and were not independently committed while MERGE_HEAD exists. Independent review must confirm the fix before installation/delivery.

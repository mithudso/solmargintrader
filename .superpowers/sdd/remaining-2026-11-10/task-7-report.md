# Task 7 — M8 guarded executor integration

Version: 1.0.0
Delta: implemented shared executor wallet authority, exact caller intents and guarded optional manager delegation; executor 0.1.0 -> 0.2.0 with synchronized uv.lock.

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

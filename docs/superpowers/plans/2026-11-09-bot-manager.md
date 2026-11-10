# Standalone Solana Bot Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one persistent CLI application for the full research-to-paper-to-gated-live bot lifecycle, sharing existing evidence and owner controls.

**Architecture:** Python modular application, one durable supervisor, SQLite event/state ledger, pure strategy adapters and versioned process adapters to legacy owners. Shared data and experiment ownership prevent duplicate recording and repeated holdout use. The first release offers useful inventory/defaults/delegated controls without a new trading loop.

**Tech Stack:** Python 3.13, argparse, SQLite, subprocess/Unix sockets, existing NumPy simulation dependencies; existing executor environment remains separate.

**Spec:** /Users/mitch/dev/solmargintrader/docs/superpowers/specs/2026-11-09-bot-manager-design.md

Version: 1.0.5
Delta: v1.0.4 to v1.0.5; record delivered editing and verified M3 source/installed behavior with explicit remaining venue gates.
Delta: v1.0.3 to v1.0.4; add owner-requested revision editing before milestone3, record delivered milestone2 and preserve the explicit all-remaining-milestones scope.
Delta: v1.0.2 to v1.0.3; record verified milestone2 source and installed acceptance.
Delta: v1.0.1 to v1.0.2; record approved implementation and delivered milestone1.
Delta: v1.0.0 to v1.0.1; resolve the reviewed milestone-2 dependency on future adapters and data.
Status: owner approved implementation in KNOW-1115. Milestones1–2 and editing delivered through PR175, PR180 and PR186. M3 source and installed acceptance passed; final-head CI/remote delivery remains its final gate. All remaining milestones4–8 are authorized and continue in order.

## Global constraints

- Default is paper/disarmed; initial scope is Solana spot, long-or-flat, SOL/USDC.
- Backtester remains offline and simulation-only. No engine network access.
- Every configurable field has a typed default or deterministic resolver; missing observations/credentials remain blockers.
- No manual pin, risk cap, existing recorder/optimizer or external owner changes silently.
- Preserve exact strategy/timeframe/execution-model semantics. No Coinbase-to-Jupiter certification by relabelling.
- One application command registry per owner. Browser actions belong in /Users/mitch/dev/solmargintrader/extension/src/core/commands.js.
- No secret material in output, logs, artifacts or browser synchronization.
- Each milestone ships through its own passing PR. Product code needs design acceptance before implementation; owner approval KNOW-1115 follows planning PR171.

## Review focus

1. Short-lived CLI processes cannot own unattended jobs; mutators target a durable owner or clearly report unavailable capability.
2. A closed/offline browser cannot acknowledge a bot-control request; no simulated success.
3. Old owners do not honor a new manager's lease; no transfer without a quiescence receipt.
4. Missing Jupiter route/cost history cannot produce a certified arbitrage backtest.
5. Changed code, timeframe, candidate ID or bot ID cannot reopen exposed final evidence or multiply wallet risk limits.

## Dependency order and useful releases

| Milestone | Depends on | Independently useful outcome | Exit gate |
|---|---|---|---|
| 1. Inventory and stable bot specifications | none | CLI inventory, provenance-aware defaults, persisted drafts and delegated legacy control | Contract/fresh-process tests; no implicit service start |
| 2. Multi-instance paper runtime | 1 | Same-family grid reference-paper bots survive CLI exit and crashes | Crash/restart/stop/accounting parity; Coinbase research label |
| 3. Shared strategy and Solana data certification | 2 | Honest five-family replay and new Jupiter paper feed | Venue/model-specific manifests and parity |
| 4. Blind evaluation | 3 | Reproducible anonymous candidate decisions | Isolation, exposure ledger, reject/accept fixtures |
| 5. Diagnostics and monitoring | 2–4 | Complete operation/P&L/performance reporting | Accounting identities, 10-bot fault/load acceptance |
| 6. Learning and promotion | 4–5 | Loss diagnosis and validated scoped improvements | Loser rejection, pins, safe adoption/rollback |
| 7. Browser integration and migration | 1–2,5 | Actual browser discovery and delegated control; later transfer | Real browser/owner receipt acceptance |
| 8. Gated live integration | 3–7 | Verified unattended execution for supported families | Independent economic verification and fresh installed evidence |

Milestones 5 and 7 can be developed before learning; do not wait for a profitability result to deliver useful diagnostics. Every earlier milestone can report unsupported live/arbitrage capabilities without pretending the full system exists. Estimates should follow the milestone-1 contract spike; fixed calendar promises would be unsupported now.

## Milestone 1 — fully specified first slice

### Task 1. Typed bot specifications and CLI registry

Create /Users/mitch/dev/solmargintrader/botmanager/pyproject.toml, /Users/mitch/dev/solmargintrader/botmanager/README.md and /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/{__init__.py,__main__.py,domain.py,config.py,registry.py,cli.py,store.py}. Declare the `solbot` console script and Python >=3.13. This brace list is a file map; the implementation should create each file explicitly. First slice uses stdlib only; numeric adapters are lazy optional imports until milestone 3.

Contracts:

- `BotSpec`: schema_version, UUID bot_id, unique display name, source identity/owner, strategy/version, mode, mints, bar seconds, execution model, config revision/hash and resolved values/provenance. Preserve user overrides separately from effective values.
- `resolve_config(strategy_id, context, overrides, shared_snapshot) -> ResolvedConfig`: accept compatible shared defaults only. Return every field's source and compatibility reason. Pin immutable settings on create. Restart never resolves defaults again.
- `ManagerStore.create_spec(spec)`, `get_spec(id_or_name)`, `append_event(event)`: transactions enforce identity uniqueness and atomic spec/event creation. Data home defaults to /Users/mitch/.config/solbot (resolved from the actual user home), tests use `SOLBOT_HOME`. Schema migrations and backup descriptor are versioned.
- Registry `dispatch(name, params, context) -> envelope`. `cli.py` only parses, dispatches, renders and selects exit code. `list`/`status` cannot create a store; missing home returns an empty/not-initialized view.
- Implement create/list/config/status and help first. Advertise start/stop only for advertised owner capabilities; own draft start says `runtime_not_available` until milestone 2. No command claims a bot is running from desired state alone.

- [x] Write tests in /Users/mitch/dev/solmargintrader/botmanager/tests/test_config.py, /Users/mitch/dev/solmargintrader/botmanager/tests/test_store.py and /Users/mitch/dev/solmargintrader/botmanager/tests/test_cli.py for pinned defaults, compatible learned settings, manual overrides, explicit zero/false, nonfinite/unknown refusal and second-process persistence. Add a canary credential and assert it never appears in envelopes/logs.
- [x] Run the focused suite and confirm it fails because the new package does not yet exist.
- [x] Implement the minimum modules; document grid/DCA/trend/momentum constructor defaults with source revision. Arbitrage initially reports `Solana adapter unavailable`, and Council is external-only.
- [x] Verify in fresh processes with an isolated temporary `SOLBOT_HOME`. Create two grid drafts with different ranges; list both, stop/inspect by identity, reload and confirm neither settings snapshot changes. Test reads leave a nonexistent data home nonexistent.
- [x] Run the suite, inspect the diff, then commit owned files with prompt/memory version updates. No production state or package installation is required to test this slice.

Source verification command for the delivered first slice:

```bash
PYTHONPATH=/Users/mitch/dev/solmargintrader/botmanager/src python3 -m unittest discover -s /Users/mitch/dev/solmargintrader/botmanager/tests -t /Users/mitch/dev/solmargintrader/botmanager
```

Here `PYTHONPATH` is an explicit source-test setting, not the production dependency contract. Package installation acceptance uses an isolated environment and its installed `solbot` entry point.

### Task 2. Legacy inventory and delegated controls

Create /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/adapters/{__init__.py,soltui.py} and /Users/mitch/dev/solmargintrader/botmanager/tests/test_legacy.py. Add installation descriptors with source, installation ID, explicit working directory/interpreter, pinned revision, protocol version and advertised commands. Do not assume the root repo is a pip-installable package. Read current API/host descriptors to choose an existing long-lived owner; no hidden server startup from discovery.

`LegacyAdapter.discover()->Snapshot`, `capabilities()->Capabilities`, `control(external_id,operation,request_id,expected_generation)->Receipt`. Descriptor contains no secret; credential resolution stays private at transport execution. Timeouts yield `owner_unreachable`; malformed/schema-new responses yield `incompatible_owner`. Inventory records config path/source hash, but direct writes to /Users/mitch/.config/soltui are forbidden.

- [x] Write fixture contract tests for available/unreachable/stale SolTUI, Council, Node FileStore and unregistered browser; test that unreachable is distinct from zero bots.
- [x] Confirm tests fail, then map actual /Users/mitch/dev/solmargintrader/soltui/commands.py descriptors: `bots.overview`, `bots.config`, `bots.forward_start`, `bots.forward_stop`, `bots.forward_status`; Council uses `council.*`. Validate params from owner discovery before a control call.
- [x] Add durable request dedup and expected configuration checks for manager-issued control. Where legacy APIs cannot guarantee idempotency after a lost acknowledgment, reconcile state and return `outcome_unknown`; never blindly retry. Family-keyed legacy start cannot create another same-family instance.
- [x] Add safe CLI discovery/status and delegated start/stop for supported reachable owners. Show browser `registration_required`; do not treat Node FileStore as the browser. Transfer remains unsupported pending milestone 7.
- [x] Verify fixtures and read-only actual discovery against the installed owner, recording loaded identity and envelopes. If unavailable, ship the tested adapter with its explicit limitation; do not start services to make a status command succeed.
- [x] Run focused tests, package/help acceptance and docs checks, then commit/push/PR/CI/merge this first useful release. Document that new autonomous runners and browser management remain future milestones.

Milestone-1 acceptance: one installable CLI, durable named specs with complete default provenance, accurate inventory, safe supported delegated controls, explicit unavailable capabilities, zero unexpected process/network/database mutation during read-only status. No claim of five running new bot families.

## Milestone 2 — persistent multi-instance paper runtime

Create /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/{supervisor.py,worker.py,transport.py,ledger.py}, /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/strategies/{__init__.py,base.py,grid.py}, a read-only recorded-input adapter in /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/data.py, and /Users/mitch/dev/solmargintrader/botmanager/tests/{test_supervisor.py,test_recovery.py,test_paper.py}. This milestone owns the minimum grid strategy/data vertical slice. Read current Coinbase recordings through an explicit installation descriptor and run existing pure gridsim in bounded replay. Label runs reference_paper with venue=coinbase_proxy. They prove unattended operation but cannot certify Jupiter execution or promote to live. Fixtures cover crashes; installed acceptance also uses actual read-only recording input. Milestone 3 expands the adapters and supplies Solana venue certification. No future milestone-3 module is needed to run milestone 2.

- [x] Write failing tests for duplicate start, crash before/after event commit, saved stopped intent, stale generation, two grid instances, a dead worker, hung tick, corrupted checkpoint and ledger reconciliation.
- [x] Implement desired/observed states, local socket commands, per-instance lifetime flock, durable idempotency, bounded worker pool/queues and transactional generation fencing. Delegate shared simulation helpers; do not fork strategy algorithms.
- [x] Add explicit service install/uninstall/status using a stable installed package location, never a disposable worktree. macOS launchd first; other supervisors are later adapters. Read commands cannot install it. Verify a requested stop survives supervisor restart.
- [x] Force-crash/restart tests reproduce identical lots/cursors/P&L to continuous replay, with no repeated fills. Test process liveness separately from data/tick progress. Stop retains positions, and independent virtual accounts are labelled.
- [x] Verify installed revision and behavior with live-acceptance-verifier before release. No live orders. Run manager suite plus changed shared simulation suites, documentation gates, then deliver. Delivered through PR180, merge2810f4b23cbd7842dcf03924608e7cb758836ee8. The installed acceptance and final-head CI receipts are recorded in the handoff; this does not certify Jupiter paper or live execution.

## Owner-requested editing extension — after milestone2, before milestone3

The owner requested editing and then clarified the scope as **all remaining milestones**. This is an additive interface requirement, not a replacement for milestones3–8. Tracking: TASK-1178. Safe adoption decision: KNOW-1179.

- [x] Add `edit BOT --set KEY=VALUE`, optional expected-revision CAS and durable request IDs. Append immutable saved revisions. Preserve every unspecified value, provenance and manual pin. Editing never changes a worker's pinned configuration.
- [x] Add `history BOT [--revision N]` with immutable revision bodies and attributed archived/current runs. Read old stores without creating or migrating them.
- [x] Add explicit `apply BOT` at a verified stopped, owner-released, zero-exposure and reconciled reference boundary. It never starts a worker. Archive the complete old run before admitting a new stopped runtime; retain fills, checkpoints, events and request receipts. Refuse unresolved state, incompatible inputs and stale expected revisions. Reapplication is a no-op.
- [x] Expose `schema [STRATEGY]` from the real shared validation/registry definitions for the later graphical client. Separate saved and active configuration identities, pending changes and adoption blockers in status. No backend capability follows merely from a UI button.
- [x] Test migrations, immutable history, cross-process edit/apply races, old-generation fencing, request replay/transplant refusal, active/exposed run preservation and fresh CLI behavior. Delivered through PR186, merge13525f2a27bc96d68dcab2a90059c2b11e1791dc after50installed checks and all11activeCIjobs passed. Milestone3 continues.

Initial adoption intentionally requires zero exposure. A later learning transition must preserve outstanding inventory and pass its own evidence and owner boundary; it cannot bypass these checks. Saving a revision is still permitted while a worker runs or holds lots. A changed specification is not a change to an active run.

## Milestone 3 — shared strategy semantics and certified Solana evidence

Create /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/strategies/{base.py,grid.py,dca.py,trend.py,momentum.py,arbitrage.py}, /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/data.py and /Users/mitch/dev/solmargintrader/botmanager/tests/{test_strategy_parity.py,test_data.py}. Add a shared package/export only after deciding ownership and packaging of pure backtester routines; preserve existing imports with compatibility wrappers.

- [x] Test batch/stream/prefix/restart parity, timeframe mismatches and grid ladder versus threshold-swap distinctions. Include intentionally leaky/future-quote fixtures.
- [x] Inventory actual data files with manifests. Read existing Coinbase owner data; implement Jupiter-specific quote collection as one shared data capability with explicit setup, rate budget and source metadata. Never generate synthetic historical routes as real evidence.
- [x] Add immutable snapshots/high-watermarks, complete/proxy/incomplete/unsupported states, size/fee/latency/fill models and no-engine-network tests. Store the actual costs or refuse certification.
- [x] Implement Solana cycle opportunity/paper replay only when required observations exist. Refuse live multi-leg execution without atomicity and a verifier. Proxy history remains exploratory.
- [ ] Validate known profitable/losing hand-calculated paths after all costs and failed legs; make replay and forward results comparable for each execution model. Deliver capabilities and measured data gaps separately.

M3 evidence: reviewed source bfc6d2f4,168 manager tests plus31 final covering tests,1002 canonical,68 Oracle,8 Trend and58 installed gates passed. Two actual post-activation accounts progressed across restart. Direct single-leg route evidence is supported conditionally; production Jupiter cost/fill history and execution certification remain unavailable. Final-head CI/remote delivery is not inferred from these checks.

## Milestone 4 — isolated blind parameter evaluation

Create /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/{research.py,blind.py}, /Users/mitch/dev/solmargintrader/botmanager/tests/{test_blind.py,test_research.py}; extend the existing evidence owner in /Users/mitch/dev/solmargintrader/soltui/experiments.py and /Users/mitch/dev/solmargintrader/soltui/experiment_runner.py with backward-compatible versioned contracts.

- [ ] Start with failing tests: parameter/incumbent metadata leak, judge mapping access, fabricated ID, relabelling/row-order invariance, exposed dates under a new fingerprint, insufficient trade samples, cost-driven loser, cancellation after unseal and pinned config changing before adoption.
- [ ] Implement typed allowlisted judge packets, private resolver mapping, frozen objective/search budgets, proposed 50/25/25 chronological partitions with purge/embargo, deterministic judge and one frozen challenger. Keep original partitions for legacy experiments.
- [ ] Reuse one exposure/reservation authority across all clients. Add cross-process serialization and repeated-attempt scope/budget controls. Persist failed and rejected trials; no new bot ID resets testing history.
- [ ] Implement final incumbent comparison with fresh independent time blocks, preregistered confidence policy, explicit insufficient evidence and atomic adoption receipt. Do not count correlated cells as independent binomial trials.
- [ ] Run /Users/mitch/dev/solmargintrader/soltui/tests/test_experiments.py and /Users/mitch/dev/solmargintrader/soltui/tests/test_experiment_runner.py plus manager tests; verify no legacy holdout mutation. Deliver before enabling unattended optimization.

## Milestone 5 — accounting, diagnosis and performance monitoring

Create /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/{health.py,reports.py} and /Users/mitch/dev/solmargintrader/botmanager/tests/{test_accounting.py,test_health.py,test_reports.py}.

- [ ] Assert equity/P&L/cash-flow identities with fees, rent, partial closes, deposits/withdrawals, missing marks and unreconciled balances. Realized/unrealized and paper/live must never collapse into one total.
- [ ] Implement human summary plus JSON/CSV, `status --why`, event timeline, config provenance, training/selection history and replay references. Metrics have units and source age; missing values remain null with reasons.
- [ ] Test 10 paper bots, one optimizer, shared rate limiting, slow worker and disconnect; enforce the design's status/stop/detection SLOs under the documented fixture load. Record measured resource usage rather than invent capacity.
- [ ] Verify backup/restore on a copied ledger, log rotation with evidence retention, alert dedup/resolution and performance warnings based on sample-aware baseline distributions. Deliver independently of learning success.

## Milestone 6 — learning without unvalidated mutation

Create /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/learning.py and /Users/mitch/dev/solmargintrader/botmanager/tests/test_learning.py.

- [ ] Tests distinguish incorrect forecast, net-loss trade, execution fault and missing data. A normal loss alone must not mutate settings.
- [ ] Add bounded parameter proposals on all eligible resolved data with loss-cohort explanations, daily schedule, >=300 labels/>=30 completed trades, one proposal per scope and 48-hour cooldown as proposed defaults.
- [ ] Require blind/fresh-final evidence plus >=7 days and >=30 shadow-paper trades before automatic paper promotion; preserve manual pins, compatible context and compare-and-swap baseline. Test that evidence failure retains incumbent.
- [ ] Test safe config boundary and rollback while lots/intents exist. Publish scoped compatible learned defaults through the existing owner protocol, not direct file overwrite. Never change risk rails or global strategy defaults from one coin's result.

## Milestone 7 — actual browser discovery and gradual owner migration

Modify /Users/mitch/dev/solmargintrader/extension/src/core/commands.js, /Users/mitch/dev/solmargintrader/extension/src/bg/soltui-transport.js, /Users/mitch/dev/solmargintrader/soltui/native_host.py and manager's /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/adapters/extension.py. Add owner protocol tests and /Users/mitch/dev/solmargintrader/extension/test/bot-manager.test.js.

- [ ] Test native registration, stable installation identity, request/result dedup, browser offline timeout, stale generation/config, no vault material and hostile command requests. Classify added commands in the extension e2e safety allowlist.
- [ ] Implement extension-initiated registration/polling through native messaging and registry dispatch. Expose capability-limited snapshot/control; do not read Chrome databases externally.
- [ ] Add prepare/quiesce/snapshot/commit transfer only with durable receipts, no pending unknown intents and both sides' generation support. Until then delegate management to old owner.
- [ ] Real-browser acceptance verifies actual browser store identity, start/stop paper state and offline behavior. Run extension parity/unit/e2e and relevant native host tests; bump extension package/manifest version for changed installed source. Use live-acceptance-verifier, then deliver.

## Milestone 8 — future live path, separately gated

Modify only verified contracts in /Users/mitch/dev/solmargintrader/executor/src/executor and manager /Users/mitch/dev/solmargintrader/botmanager/src/botmanager/adapters/executor.py; read /Users/mitch/dev/solmargintrader/executor/CLAUDE.md again first.

- [ ] Resolve venue choice explicitly: retain owner-selected v1 boundary unless a v2 migration is requested. Implement independent economic verification before v2/Trigger signing; unknown routes/instructions refuse. Arbitrage remains live unsupported without atomic construction and verification.
- [ ] Test wallet-level atomic capital reservation, per-strategy aggregate limits across instance IDs, kill/loss stops, fee/size/price missingness and unknown-submit recovery. One shared executor writer must fence other live surfaces.
- [ ] Prove exact transaction simulation, research/soak gates and current installed identity. Live activation and any tiny transaction test follow existing owner authorization and current caps; this plan does not execute them.
- [ ] Complete independent installed behavior acceptance and journal/chain reconciliation before claiming autonomous live support for a strategy. Release only the certified strategy/venue/model combinations.

## Verification and delivery policy

Every task follows fail-first meaningful tests, minimal implementation, completed successful checks, review, versioned prompt/memory update and its own owned commit. Commands above are future verification specifications, not results from this planning run. Manager tests use isolated state and network fixtures; external API integration tests follow current official contracts and suitable mocks. No fixture test can stand in for installed browser/service acceptance.

For shared code changes use existing suites and environments from /Users/mitch/dev/solmargintrader/docs/TESTING.md and component instructions. Run /Users/mitch/dev/solmargintrader/scripts/check_docs.py and offline repository metadata regeneration/check at delivery. Stage explicit owned paths, push, wait for final-head CI, merge, verify remote contents and clean only the task's merged worktree. Preserve concurrent research, installed services, active bot state and all unrelated work.

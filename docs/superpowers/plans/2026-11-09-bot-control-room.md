# Bot Control Room Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the proposed bot fleet and studio into the existing extension without creating another execution engine.

**Architecture:** Use framework-free ESM presentation, pure view models and validated drafts. Consume existing registered commands and Python owner receipts through the current bridge. Add backend fields only when the screen needs data the current snapshot cannot supply; missing fields remain unavailable.

**Tech Stack:** Existing HTML/CSS/ESM, Node 22 node:test, current Python 3.13 components and real-browser fixture harness. No new runtime dependency.

**Spec:** /Users/mitch/dev/solmargintrader/docs/design/bot-control-room/DESIGN.md

Status: proposed future product implementation. All checkboxes are intentionally open. This design task does not authorize a new live runner, arming, account migration or retired liquidity service activation. Re-read current component instructions and CLI design TASK-1092 before execution; sources may move after this plan's baseline `4d4c7a1`.

Plan version: 1.0.1. Delta: v1.0.0 to v1.0.1; bind stable draft IDs to existing backend runtime-slot limits after builder review. The first release permits multiple named drafts but only one active session per supported backend strategy slot. Multiple active instances of the same strategy/market require a future backend capability and are not part of this plan.

## Global Constraints

- Paper simulation and disarmed capability are the default.
- Separate backtest, paper and live results.
- Unknown requires venue/chain reconciliation; never auto-retry.
- The UI cannot weaken engine rails.
- Missing values remain unavailable.
- Secrets never enter the UI.
- Manual mode freezes the user's values.
- Multiple markets create separate configuration/evidence identities.
- Every new extension action belongs in /Users/mitch/dev/solmargintrader/extension/src/core/commands.js.
- No framework, npm runtime dependency or copied strategy logic.
- Current unsupported venue/product/action capability stays blocked.
- Duplicate creates a new draft UUID; it never replaces an active runtime session.
- Default runtime ownership is the existing backend strategy slot, not an assumed strategy/market pair.

## Review Focus

1. Missing, NaN or partially migrated financial fields must display Unavailable and block affected actions; owned by Task 1.
2. Market switching during a slow response must reject the obsolete response and preserve the new selection; owned by Task 2.
3. Concurrent manual edit and automatic proposal must preserve manual mode and detect version conflict; owned by Task 3.
4. Double-click, reconnect or worker interruption must not duplicate a paper owner or classify unknown submission as absence; owned by Task 4.
5. Partial pause and stale/held bot state must disclose remaining activity/exposure, preserve focus and never claim canceled orders; owned by Tasks 2 and 4.

## File structure and boundaries

All new production paths below are proposed. Inspect current counterparts before creating a duplicate. Keep the standalone mockup as a reference; do not load it as an extension page.

| Files | Responsibility |
| --- | --- |
| /Users/mitch/dev/solmargintrader/extension/src/ui/bots/model.js | Pure normalized bot/evidence/capability view data |
| /Users/mitch/dev/solmargintrader/extension/src/ui/bots/fleet.js | Roster, selection, filter/sort, inspector and incidents |
| /Users/mitch/dev/solmargintrader/extension/src/ui/bots/studio.js | Versioned five-stage draft, field units and review |
| /Users/mitch/dev/solmargintrader/extension/src/ui/bots/workflow.js | Receipt-backed paper workflow state and scoped actions |
| /Users/mitch/dev/solmargintrader/extension/src/ui/bots/bots.css | Scoped components, responsive layout and token mapping |
| /Users/mitch/dev/solmargintrader/extension/src/ui/dashboard.html and /Users/mitch/dev/solmargintrader/extension/src/ui/dashboard.js | Existing workspace integration and accessible route ownership |
| /Users/mitch/dev/solmargintrader/extension/test/bot-model.test.js, /Users/mitch/dev/solmargintrader/extension/test/bot-studio.test.js, /Users/mitch/dev/solmargintrader/extension/test/bot-workflow.test.js | Pure/state and command contract regressions |
| /Users/mitch/dev/solmargintrader/extension/e2e/bots.mjs | Proposed isolated-browser scenarios, integrated using the current harness conventions |

Do not create a separate route server or signer. Integration that needs a missing backend feature belongs in a separate scoped task with its own component rules, tests and current API documentation.

### Task 1: Normalize honest bot and evidence state

**Files:** Create the proposed model and model test paths above. Inspect /Users/mitch/dev/solmargintrader/soltui/bots.py, /Users/mitch/dev/solmargintrader/soltui/paper_workflow.py, /Users/mitch/dev/solmargintrader/soltui/commands.py and /Users/mitch/dev/solmargintrader/extension/src/core/commands.js for current envelopes.

**Interfaces:**
- Consumes current command envelopes, using exact source fields discovered before implementation.
- Produces `normalizeBotSnapshot(raw, nowMs) -> BotView[]`, `evidenceCompatibility(a, b) -> {compatible: boolean, reasons: string[]}` and `deriveAllowedActions(bot) -> {action: string, allowed: boolean, reason: string|null}[]`.
- `BotView` carries `id`, `runtimeSessionId`, `runtimeSlot`, `configVersion`, `market`, `mode`, `lifecycle`, `inputState`, `heartbeatAtMs`, `decisionAtMs`, `decisionReason`, nullable `allocationUsd`, `exposureUsd`, `realizedNetUsd`, `unrealizedNetUsd`, `costsIncludedUsd`, `evidenceRefs`, `unknownSubmissionCount`, and explicit `capabilities`. `runtimeSlot` reflects actual owner scope; absent `per_instance` support defaults to the current strategy-scoped owner. No absent number becomes zero.

- [ ] Write `bot-model.test.js` cases for missing/NaN fields, old heartbeat, fresh heartbeat with stale market input, unknown submission, missing capabilities, negative valid result and incompatible cost/data identities. Assert actions fail closed, result stays null and evidence dimensions remain separate. Two drafts of one strategy must resolve to the same existing runtime slot until explicit instance support is present.
- [ ] Run `cd /Users/mitch/dev/solmargintrader/extension && node --test test/bot-model.test.js`; verify the missing model fails before implementation.
- [ ] Implement the signatures above as pure functions. Map current source envelopes explicitly and document unsupported fields. Use the existing command registry for any necessary normalized read command; preserve CLI/API/UI parity.
- [ ] Run the focused test and `node --test test/surfaces.test.js`; expect complete success.
- [ ] Review the diff and commit only the model, tests and required registry mapping. Do not modify execution logic to fill a display gap.

### Task 2: Integrate fleet and operational inspector

**Files:** Create fleet.js and bots.css; modify the existing dashboard entry paths. Add browser cases under the current e2e runner's registration conventions.

**Interfaces:**
- Consumes Task 1 `BotView[]` and allowed actions.
- Produces `mountFleet(root, {loadSnapshot, requestAction, now}) -> {dispose()}`. `loadSnapshot()` resolves current envelopes; `requestAction(name, params)` is provided by the existing dashboard command dispatch, not a new transport.
- Retain `{selectedBotId, filter, sortKey, sortDirection}` as user state. A monotonic request generation binds responses to their requested market/scope.

- [ ] Add fixture scenarios: keyboard-select a bot, refresh while sorted, filter with no results, switch markets during a delayed old response, and inspect one unknown/stale bot. Assert mode, currency/period, last decision, missing-value labels and exposure are visible without focus loss.
- [ ] Run only these browser scenarios using the existing runner's selectors; verify meaningful failure before integration. Derive the exact invocation from /Users/mitch/dev/solmargintrader/extension/tools/e2e.mjs rather than inventing an unsupported flag.
- [ ] Implement fleet and inspector using native semantics and scoped CSS. Preserve existing dashboard routes and chart attribution/CSP. At ≤720px use stacked content; no page-wide overflow at 320px. Add an accessible chart table and real source/gap labels before showing measured equity.
- [ ] Add incident links, actor/source attribution and capability explanation. Distinguish external wallet events from bot-owned events.
- [ ] Run the affected browser scenarios and model tests at 1440px, 1000px, 720px, 390px and 320px. Check text enlargement, keyboard order, reduced motion, dialog return focus and color contrast. Commit the verified integration.

### Task 3: Build schema-driven, versioned Bot studio

**Files:** Create studio.js and bot-studio.test.js; extend bots.css and dashboard integration. Read current config schemas and validators rather than cloning the prototype's abbreviated forms.

**Interfaces:**
- Consumes current bot parameter schema, effective limits and saved configurations through existing read commands.
- Produces `createDraft({strategy, market, schema, effectiveLimits}) -> BotDraft`, `validateDraft(draft) -> {valid: boolean, errors: {path: string, message: string}[]}` and `mountStudio(root, {draftStore, loadSchema, saveDraft}) -> {dispose()}`.
- `BotDraft` has stable UUID `id`, `schemaVersion`, `baseConfigVersion`, `strategy`, `market`, `mode: 'paper'`, typed `parameters`, `tuningMode`, `limits` and `costModelId`. Duplication assigns a fresh UUID and retains source evidence only as a reference, not as evidence for changed parameters. No credential fields.

- [ ] Write tests for all five bot choices, Grid spacing alternatives, exact units/defaults, per-market isolation, whitespace name, absent fee/price inputs, full parameter round-trip, invalid cross-field values and conflict between a manual edit and automatic proposal. Assert a stale `baseConfigVersion` preserves the draft and refuses overwrite.
- [ ] Run `node --test test/bot-studio.test.js` from /Users/mitch/dev/solmargintrader/extension; verify missing implementation fails.
- [ ] Implement the five-stage flow with visible labels, inline error links, back navigation and persisted safe drafts. Use backend validators for saving effective configuration; a UI draft never changes an active bot.
- [ ] Add current/proposed diff and per-market manual/automatic state. Keep “tentative” visibly separate from confirmed policy evidence. Never infer geometric spacing superiority.
- [ ] Add fixture tests that a saved draft starts no worker, reserves no capital and cannot implicitly arm. Verify escape/navigation preserves the draft. Run focused tests and commit.

### Task 4: Connect explicit paper preparation and scoped controls

**Files:** Create workflow.js and bot-workflow.test.js; modify registry mappings only if current commands lack the required supported operation. Any Python modification requires its own component review and focused tests.

**Interfaces:**
- Consumes current paper-workflow `status`, `ensure` and `stop` receipts, bot-specific capabilities and current registry dispatcher.
- Produces `normalizeWorkflowReceipt(raw) -> WorkflowView` and `mountWorkflow(root, {dispatch, refresh, botId}) -> {dispose()}`.
- `WorkflowView` retains per-stage state, worker owner, completed/failed/skipped counts, error reason, per-bot outcomes and last acknowledged receipt. An unacknowledged stop is pending, never stopped.

- [ ] Write tests for duplicate Start, a second named draft of the same strategy, a different market sharing its strategy-scoped slot, reconnect, interrupted owner, partial preparation, failed measurement versus valid loss, held bot resume refusal, unknown submission refusal and partially successful bulk pause. Assert an occupied slot offers its existing session and refuses replacement without starting or reserving capital. Assert independent workers continue unless their own supported stop was acknowledged.
- [ ] Verify tests fail before adding new behavior. Inspect existing /Users/mitch/dev/solmargintrader/soltui/tests/test_paper_workflow.py for duplicate-owner and stop-scope guarantees.
- [ ] Reuse the existing coordinator with idempotent intent dispatch and receipt-based stage updates. Never map per-bot Pause entries to coordinator stop. If backend pause capability is absent, expose the reason and deliver it in a separate backend task before enabling the control.
- [ ] Add current capability inspection. Live automation remains unavailable when missing or blocked. Preserve the separate owner-chosen fast/no-confirmation policy on supported manual paths; do not add a new live path in this task.
- [ ] Run focused JS tests, the registry parity suite and any touched Python workflow tests. Verify partial failures remain visible, then commit.

### Task 5: Owner validation, integrated acceptance and delivery

**Files:** Extend the existing fixture suite and component documentation; record actual validation in /Users/mitch/dev/solmargintrader/docs/design/bot-control-room/REVIEW.md with a new version/delta.

**Interfaces:** Consumes the integrated routes and accepted command/evidence contracts from Tasks 1–4. Produces a revision-bound acceptance receipt, not a claim of profitable live trading.

- [ ] Ask the owner to complete the five tasks in the design's validation section. Record actual outcomes and unresolved confusion; synthetic reviewers are not participants. Resolve observed blocking design issues before calling the interface validated.
- [ ] Run extension unit/syntax checks and the real-browser fixture gate; run affected Python suites if changed. Run `python3 scripts/check_docs.py` and offline retrieval-index freshness checks after explicit owned paths are staged. Do not enable the optional full SolTUI suite or paused services merely for this UI change.
- [ ] Package/install only if the authorized product implementation includes an installed extension change. Use independent loaded-revision verification as the final behavior gate. Verify mode, held states, draft persistence and supported command receipts in the actual loaded revision.
- [ ] Review task-owned diff; commit/push, open PR, await final-head required CI, merge, verify remote default-branch content and preserve other active worktrees. Complete tracking only after that receipt.

## Self-review

Spec coverage: fleet, studio, evidence and activity belong to Tasks 1–3; owner/job semantics and capability boundaries belong to Task 4; accessibility, owner research and installed acceptance belong to Tasks 2 and 5. Complete strategy schemas, version conflict and per-market identity are explicit in Task 3. Position/order drilldown needs real data before visualization, covered by Task 2's source mapping and missing-value rule.

All five Review Focus cases have owning tests. Signatures use one name throughout. No planned function implements signing or bypasses authoritative risk checks. This is a staged product plan; the design prototype does not satisfy these implementation gates. Recommended execution is native implementation with an independent final review because Tasks 1–4 share view and command contracts. The owner can revise the proposed platform or scope before product implementation.

# Task 5 independent review

## Final re-review — commit 6d7af982f1e18ba4959d5ed4e22fa3a5b8a31805

SPEC COMPLIANCE: PASS for reviewed Task 5 source scope, with explicitly unavailable comparable Oracle forecast attribution and pending production qualification retained.

CODE QUALITY: PASS. All original findings, the exact shadow-pair binding gap and the follow-up oversized-clock finding are closed. No remaining blocking finding was identified in this review scope.

The exact final diff introduces a shared clock validator that checks integer/float type and the inclusive 0..253402300799 range before any float conversion. NaN, infinity, booleans, negative values and arbitrarily large JSON integers are rejected. Both top-level clocks and nested timestamp keys use that validator; local read and helper polling also sanitize OverflowError. Added actual Supervisor and helper subprocess regressions cover positive/negative 401-digit integers, smaller out-of-range integers, unchanged malformed local files, responsive status and helper reaping. Accepted the supplied completed 15-test scheduler/bounded-read receipt and clean Ruff result; no broad suite rerun was necessary.

The prior 13e229f fixes remain unchanged: bounded proposal/legacy pointer round trips, original Oracle provenance retained as explicitly ineligible, forecast scan overflow refusing incomplete totals, and exact shadow configuration plus immutable activation binding. The earlier 98-test covering receipt remains applicable to those unchanged fixes.

This is source review acceptance only. Independent installed acceptance and remote delivery remain controller gates. Current production source certification, actual seven-day prospective operation and thirty comparable completed shadow trades remain pending; fixture success establishes none of those production claims. Historical failed verdicts below are superseded by this final disposition.

## Re-review — commit 13e229f5a3197438c3e617d2dc39b42adc65e157

SPEC COMPLIANCE: FAIL pending one remaining malformed-status lifecycle boundary.

CODE QUALITY: FAIL pending the reproducible OverflowError below. All four original numbered findings and the exact shadow-pair binding gap otherwise close on source inspection and the supplied 98-test passing receipt. No broad suite was rerun.

### Remaining P2 — oversized integer clock escapes scheduler validation

Location: /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/learning_job.py:109 (`math.isfinite(body[key])`).

The new clock schema accepts an integer before calling math.isfinite. Python converts integers to float for that call and raises OverflowError for a sufficiently large integer. A valid JSON local receipt containing state=running, reason=x and last_attempt equal to 10**400 is under 1KiB, but both schedule_snapshot(home) and DailyLearningJob(home) raise `OverflowError: int too large to convert to float`. The reader catches ValueError, TypeError, OSError and RecursionError, but not OverflowError; supervisor construction therefore still depends on optional malformed metadata. The same validator is used for helper results. Reproduced with only a temporary home, no installed or production state.

Range-check integer clocks before float conversion, or translate OverflowError into the same unavailable/failed outcome at every validation boundary. Add the oversized integer case to the actual supervisor-boundary regression.

### Closed findings and retained limits

- Original P1 pointer schema: producer now projects integer counters and a separate bounded cohort map; the reader supports both that representation and bounded legacy summaries without mutation. Existing scan/byte/SQLite budgets remain. The added actual owner-proposal round trip covers this contract.
- Original P2 forecast attribution: actual Oracle forecasts retain original source/model/parameter/version/horizon/policy provenance and named ineligibility reasons. They are explicitly excluded from comparable-label totals; no alias or active fingerprint is fabricated. The actual OracleEngine archive integration covers both correct and wrong outcomes. This is an honest narrowed capability, not a claim that comparable forecast training is now available.
- Original P2 forecast overflow: query includes the sentinel row, handles row/aggregate-byte/body budgets, reports counts_complete=false and null totals, and refuses proposal publication. The added boundary and newly appended wrong-resolution tests cover the intended behavior.
- Original scheduler JSON shape failure is fixed for arrays, scalars, null and ordinary malformed fields/envelopes, with actual Supervisor lifecycle regressions. The additional integer overflow above prevents fully closing that boundary yet.
- Shadow pair gap: expected incumbent/challenger config hashes and immutable source/activation contracts now bind progress. Dynamic snapshot progress remains allowed, and the added same-runtime adoption regression invalidates the parent proposal after a challenger configuration change.

Canonical quotas, owner evidence/receipt boundaries, seven-day AND thirty-trade requirements and source certification refusal were not relaxed by the repair. Current production source certification and actual elapsed/trade qualification remain pending.

## Original review (historical findings; disposition above supersedes verdicts below)

SPEC COMPLIANCE: FAIL — the production forecast ingestion path does not implement the claimed forecast cohort coverage, and real proposal pointers cannot be inspected locally.

CODE QUALITY: FAIL — producer/consumer schema disagreement and an unchecked scheduler receipt shape cause reproducible failures. Changes are required before acceptance.

Reviewed the Task 5 brief, implementation report, frozen review package and corresponding source in /Users/mitch/dev/solmargintrader-wt-01a1c447. Scope is protected learning and its scheduler/publication boundaries; the separate continuation reviewer owns economic-engine correctness. No product files, installations, production state or services changed. Previously reported 43 targeted, 27 scheduler and 18 supervisor checks were accepted as supplied; only the focused reproductions below were executed.

## Findings

### P1 — every actual staged proposal fails its local pointer reader

Locations: /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/learning.py:329 and :406.

`record_owner_view` stores `proposal['counts']` unchanged. The canonical owner sets that field to the whole collection summary, which contains `scope` and `comparability` strings and a nested `cohorts` dictionary, besides integer totals. `learning_snapshot.pointer` accepts a counts dictionary only when every value is a nonnegative integer. The normal producer therefore always creates a pointer the normal reader rejects. Proposal creation and the daily scheduler both use this producer. Local status reports unavailable and drops the pending/shadow proposal instead of showing the guarded transition.

Reproduced in a temporary home using the actual `record_owner_view` and `learning_snapshot` functions with a canonical-shaped proposal containing 300 labels and 30 trades. Result: `state='unavailable'`, `reason='local_learning_metadata_unavailable'`, `proposals=[]`, and `local_metadata.proposals.reason='local_metadata_invalid_or_budget_exceeded'`.

Fix the bounded pointer schema at both ends. Keep integer totals and explicitly bounded cohorts, or project only the intended integer counters. Add a round-trip test using a real owner proposal rather than a hand-written simplified pointer.

### P2 — forecast cohort ingestion has no matching strategy identity

Location: /Users/mitch/dev/solmargintrader-wt-01a1c447/soltui/learning_owner.py:337.

The query filters Oracle forecasts by exact equality to the manager strategy ID. The supported learning IDs are `grid`, `dca`, `trend`, and `momentum`; the actual Oracle catalog emits `ma_crossover`, `ts_momentum`, and twelve other IDs, none matching those four. Consequently no real correct or incorrect Oracle forecast can enter the learning cohort for any supported tunable strategy. The classification unit test uses constructed forecast rows and does not exercise this ingestion boundary. A focused AST/catalog comparison printed `SQL equality matches: []`.

Define and test an explicit attribution contract for manager/Oracle identities, parameters, versions, horizons and source policy. Do not simply rename ma_crossover to trend or ts_momentum to momentum: the source forecast semantics and parameter choices must actually match. If existing Oracle forecasts cannot be comparable, retain an explicit excluded/unavailable forecast cohort and narrow the implementation claim rather than silently losing every forecast. A real archived-resolution integration test must establish the intended path.

The same query also selects only resolution data, not the forecast provenance body/version, and unconditionally assigns the current runtime comparability fingerprint. Any future identity mapping must validate original provenance before setting comparable=true.

### P2 — malformed scheduler receipt can terminate the supervisor

Locations: /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/learning_job.py:38 and :157; /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/supervisor.py:70.

The status reader accepts any syntactically valid JSON, while the job assumes an object. With `learning-job.json` containing `[]`, construction succeeds and `step()` raises `AttributeError: 'list' object has no attribute 'get'` before checking whether an owner descriptor exists. The supervisor catches only OSError and ManagerError around this optional job, so the exception escapes its loop. An optional local status receipt must not become a lifecycle dependency for unrelated workers.

Reproduced in a temporary home with no owner descriptor by writing `[]` and calling `DailyLearningJob(home).step()`. Validate receipt shape and bounded fields in the reader; return an unavailable status for arrays/scalars/null or invalid fields. Test the supervisor boundary with malformed-but-valid JSON, not only JSON syntax errors and filesystem failures. The helper output envelope also needs shape validation before `.get`, for the same reason.

### P2 — forecast ingestion silently freezes after its first 100000 rows

Location: /Users/mitch/dev/solmargintrader-wt-01a1c447/soltui/learning_owner.py:337.

The fixed query reads the oldest 100000 resolutions on every collection and never checks for row 100001 or advances a cursor. Once an attributed stream reaches that size, later outcomes are never learned and the summary still appears complete. This differs from the explicit fail-closed overflow behavior for runtime archives in the same function. This becomes reachable once the preceding attribution defect is fixed.

Use a durable incremental cursor with bounded batches, or detect overflow and fail closed with a named reason. Add a boundary test proving that newer wrong forecasts/loss cohorts are not silently omitted.

## Other assessed boundaries

Canonical scope excludes UUID, home, seed and data fingerprint; the canonical database owns daily reservations and promotion cooldowns. Explicit commands do not expose clocks, counts, certification flags or replacement evidence. M4 admission is reused under the optimizer lease, with baseline/pins, source/cost/engine comparability, authority/history, blind training and final digest checks. The source's uncertified venue compatibility still blocks actual promotion; controlled fixture certification is not production evidence.

Shadow creation uses durable pair IDs, existing worker ownership and prospective activation. Gate code requires worker-event elapsed time, source observation coverage, 30 completed trades on both runs, prospective delivery classification, common final timestamps, reconciliation health and challenger advantage. Review did not find a public client-clock/count bypass. Stronger exact pair binding would be useful: current progress validation checks runtime ID and comparability but does not compare the bound `input_hash` or expected incumbent/challenger configuration hash; reject any future configuration-adoption path that changes a shadow account under the same runtime identity.

Owner authorization precedes manager publication, local attached-database adoption requires DELETE journaling and a paused/stopped/checkpoint boundary, and manager publication reconciliation reads the bound journal rather than trusting the submitted manager receipt alone. Exact request/digest replay is idempotent. Full economic account preservation is deferred to the separately assigned continuation review. This review does not certify installed acceptance, actual seven-day operation or production shadow trade counts.

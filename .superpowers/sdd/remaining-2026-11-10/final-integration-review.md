# Final cross-milestone integration review

Version: 1.2.0
Delta: 1.1.0 to 1.2.0; reviewed the test-only Linux load-fixture correction 2dcbcac, required macOS CI load step and interface stdout clarification. Overall source SPEC/QUALITY remains PASS. Previous delta: independently re-reviewed both P2 repairs in 2431ed7d9990d64f15f7147bdf22c3419012417a and closed both findings. Includes the independently reviewed watchdog repair committed as 370c758. Original whole-branch review covered remote baseline 72819d6fd4dd9678c7b648f4236c24dc4c6b4e08 through f24ad194a541f99e4a6902a5c054d046fb90c48e. Historical reproductions remain below.

SPEC COMPLIANCE: PASS for the reviewed source scope. Both recovery/identity findings are resolved. Final full-source checks, regular installed acceptance, CI and remote delivery remain separate controller gates.

CODE QUALITY: PASS. No unresolved actionable P1/P2 remains in this targeted cross-component review. This verdict does not certify actual elapsed shadow evidence, venue execution or production live readiness.

## RESOLVED P2 — Interrupted shadow pair creation permanently separates activation contracts

Locations: /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/learning.py:295 and /Users/mitch/dev/solmargintrader-wt-01a1c447/soltui/learning_owner.py:633.

The owner durably reserves pair IDs, but shadow_pair captures a new activation descriptor on every attempt. If the process fails after incumbent registration/start and before challenger registration, the next attempt reuses the incumbent and registers the challenger with a different activation time and source watermark. start_shadow then rejects their different immutable_input bindings after both have running intent. It leaves shadow.runs unset. Later attempts retain both incompatible accounts and cannot complete publication.

Independent temporary-only reproduction used the real Oracle archive fixture, manager store, runtime ledger and shadow_pair. Source held 120 observations. At START+120, a patched RuntimeLedger.register raised RuntimeError only for the challenger. At START+121, the same pair IDs were retried without the fault. Output was activation_times=[1700000160,1700000161], immutable_bindings_equal=False, both_desired_running=['running','running']. The diagnostic completed with exit 0. No service or worker was started by the diagnostic.

Persist a single activation descriptor before either account is created, or recover the exact descriptor from an existing correctly bound pair member before creating the missing member. Validate existing members before new side effects. Add an actual owner crash/retry regression with advancing source time, unchanged pair/runtime IDs and identical immutable activation contracts. Never relabel delayed replay as prospective evidence.

## RESOLVED P2 — A valid owner adoption receipt can mutate a different restored manager home

Locations: /Users/mitch/dev/solmargintrader-wt-01a1c447/soltui/learning_owner.py:893 and /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/ledger.py:1531.

Owner authorization binds bot, runtime and configuration but omits the proposal's manager home. Backups preserve those identities. reconcile_transition applies an authorized receipt to its caller-selected ManagerStore before the owner verifies publication in the original proposal.home. A restored/copy home can therefore adopt the change even though the owner authorized and later inspects a different database. Failure occurs after the wrong home has committed its revision.

Independent reproduction used the actual LearningOwnerTests fixture, real canonical owner authorization/publication functions, a paused/stopped flat checkpoint and a copy into a different temporary manager directory. Only the existing fixture's certification and elapsed-shadow gates were simulated; no production certification was asserted. Calling reconcile_transition for the copied home produced OperationalError('no such table: learning_adoptions') when owner reconciliation read the original home. The original remained revision 1; the different selected home had already advanced to revision 2. The diagnostic completed with exit 0 after printing those observed values.

Bind the canonical proposal home into the authorization digest and reject a mismatched selected store/ledger before any database initialization, migration, receipt replay or adoption write. Keep old unbound receipts explicitly unavailable unless their original binding can be established safely. Test wrong/restored-home refusal with unchanged database bytes and successful original-home exact replay.

## Reviewed integration boundaries

Read repository instructions, remaining-work plan, handoff, Oracle interface, eight task briefs, implementation reports and seven independent review reports. Inspected the whole diff inventory (122 files, approximately 15,000 added lines), then followed the cross-component contracts rather than repeating every task-local line review.

- Runtime schema 5 gates writers; old-schema reads and append-only archived event attribution remain explicit. Immutable segment digests and fill-prefix reconciliation remain part of the read path. Active state is bounded; cumulative history verification is not a fixed-time guarantee.
- Canonical continuation and flat rebind preserve cash, retained losses/fees, initial-capital attribution, fill history and runtime identity. Selected archive reports retain historical configuration. Reports refuse oversized evidence explicitly instead of trusting unchecked totals.
- Learning consumes canonical M4 proposal/final/training identities and scoped history revisions. Current Oracle forecasts remain explicitly ineligible rather than being renamed into a comparable strategy. Actual worker/observation spans, trade counts and venue certification remain distinct gates.
- Browser origin, profile identity, source/config/runtime generation and durable receipts remain owner-bound. Valid later stops fence earlier starts; failed controls do not obtain execution authority. Source-resource checks still require fresh actual browser installation acceptance.
- Executor keeps the shared wallet writer, imported uncertainty, exact pending writer-awareness binding, conservative aggregate ceilings and held ambiguous reservations. Manager-originated live requests explicitly refuse because there is no live manager authorization issuer. This review does not broaden that capability.
- Current documentation distinguishes the 0.6 candidate from delivered historical M4 and describes the package matrix, unknown financials, external ownership, everyday-browser limitation and real production evidence gates. The current release/installed receipts remain controller work.

## Independent checks completed

Using /Users/mitch/.venvs/solbot/bin/python with explicit worktree source PYTHONPATH, seven focused integration regressions passed with final exit 0:

- account-preserving adoption and exact replay;
- crash after local adoption before owner reconciliation;
- retained realized losses and fees;
- archived report configuration attribution;
- actual owner/manager publication and rollback;
- all four canonical families across more than 2,048 bars;
- atomic prospective segment archival and restart.

The first five completed in 0.901 seconds; the two continuation tests completed in 7.623 seconds. The known synthetic annualization overflow warning appeared without affecting assertions. The two additional temporary diagnostics independently reproduced the findings above. These are source checks, not installed acceptance.

## Limits and remaining gates

Root owns full final-source checks, fresh regular installed acceptance, exact loaded-source comparison, documentation/index validation, CI and verified remote delivery. Those known unfinished gates are not code findings. The separately assigned health reviewer owns the real exclusive-SQLite-lock stall fix and its load result. No broad duplicate load diagnosis ran here.

This reviewer edited only this report, staged nothing, committed nothing and changed no production home, authority, key, service, producer, installed environment or everyday browser profile. No order or live network test ran. Real seven-day shadow operation, thirty comparable completed shadow trades and venue certification remain real gates; fixture checks prove none of them. The completed repair re-review is recorded below.

## Concurrent health repair review

Inspected the final uncommitted supervisor/watchdog repair and its tests after the health reviewer identified a frozen SQLite writer. No additional P1/P2 finding arose. Cached deadlines bind the exact owned Process and generation, preserve monotonic progress clocks, confirm blocked journal writes, terminate before journal mutation and retain generation-fenced pending failure publication. Shutdown retries the original conditional fence and explicitly reports unresolved failure writes rather than claiming reconciliation.

Independently ran both final shutdown regressions: frozen exclusive writer release before fence retry, and unavailable pending-failure publication. Both passed in 1.190 seconds with final exit 0. The health author's separate 34-test receipt reports reserved/exclusive watchdog and actual-M4 load checks passed; that broader result is supplied evidence, not independently rerun here. Source review of this repair passes. The reviewed source was subsequently committed as 370c758.

## Exact repair re-review — 2431ed7d9990d64f15f7147bdf22c3419012417a

The shadow repair preflights both planned members before creation. It validates saved and runtime configurations, requires attributed prospective input, verifies agreement between existing activation bindings and checks the original source contract. If a member already exists, its exact descriptor supplies the missing peer's activation. No fresh descriptor is captured on retry. The new peer's immutable binding must match before registration. The original outer-owner regression now advances both time and source observations after the injected first-member crash, forbids descriptor recapture, and verifies unchanged pair IDs, original activation, retained incumbent runtime, matching input bindings and absence of duplicate accounts. The actual capture function retains the descriptor's activation watermark while later progression keeps its existing delayed/prospective classification; the repair does not grant elapsed evidence credit.

The home repair includes canonical proposal.home as manager_home in the owner's digested authorization. RuntimeLedger.learning_adopt validates that canonical absolute path against both ledger and ManagerStore before obtaining a mutation lock, opening a write connection, migrating schema or checking existing replay receipts. Owner replay refuses earlier unbound authorizations. Existing home equality is therefore required even when an already-published receipt appears in a copied journal. The owner/publication regression uses actual backup and restore APIs, observes byte-for-byte nonmutation of original and restored manager databases on wrong-home refusal, then completes the same request at the original home through crash reconciliation and rollback.

Independent targeted execution used /Users/mitch/.venvs/solbot/bin/python with explicit worktree source PYTHONPATH and temporary fixtures:

- tests.test_learning.ShadowActivationRecoveryTests.test_owner_retry_recovers_first_member_activation_after_peer_crash;
- tests.test_learning.LearningTests.test_unbound_and_copied_home_authorizations_refuse_before_mutation_even_replay;
- soltui.tests.test_learning_owner.LearningOwnerTests.test_owner_manager_publication_and_rollback_preserve_account.

All three passed in 1.059 seconds, final process exit 0. The reviewed production paths had no unstaged changes and HEAD was 2431ed7d9990d64f15f7147bdf22c3419012417a. The author's 28-test/Ruff receipt is additional supplied evidence; broad suites were not repeated. The controller's c949a4e test-fixture teardown change is outside these production repairs and introduces no production job implementation change. No additional source finding arose. Both original P2 findings are closed, and the overall source SPEC/QUALITY verdicts are PASS with the release and real-evidence limits above.

## Narrow CI portability review — 2dcbcac

SPEC COMPLIANCE: PASS. CODE QUALITY: PASS. No additional actionable finding.

The failed Linux CI load fixture had called the production macOS-only resolver. Its isolation_unavailable refusal was correct. The correction changes only the explicit numerical test workload: Darwin retains the actual run_judge sandbox, while other platforms select the existing pure decide function and label the result pure_numerical_fixture_no_os_isolation with os_isolation_claimed=false. Production blind.py and blind_judge.py are unchanged and retain the unsupported-host refusal. This is not an unrestricted production fallback.

Both paths reuse the same complete ten-bot/four-worker fixture, canonical optimizer lease, actual simulation cells, crash/restart checks and strict watchdog thresholds. The extra forced-Linux test exercises that branch even on macOS. The reviewed /Users/mitch/dev/solmargintrader-wt-01a1c447/.github/workflows/ci.yml change runs test_load.py explicitly in the macOS PR/push job after installing the headless owners and running actual OS-isolation checks. The Linux fixture does not replace that real sandbox-backed load gate.

Independently verified exact callable identity and evidence labels for both branches with a completed exit-0 probe. Inspected the final /Users/mitch/.local/state/solbot/releases/0.6.0/task3-load-portable-final.log: two tests passed in 32.224 seconds. The test author confirmed the process's final exit_code=0 and Ruff exit 0. Reported watchdog ages were 14.007026 seconds for the actual macOS sandbox and 14.023086 seconds for the forced-Linux numerical fixture; both retained four active/six queued bots, uncertified source outcomes and clean optimizer exit. This load run is supplied evidence inspected by the reviewer; it was not broadly duplicated.

Also checked the interface 0.3.2 clarification against cli.py: human and CSV report formats print rendered text directly, while JSON clients receive the machine envelope. That documentation change introduces no runtime behavior. Packaged wiki asset refresh and current installed asset parity remain the controller/installed-verifier scope. Final CI and remote delivery still require their own successful receipts. No product source, installation or live state changed during this narrow review.

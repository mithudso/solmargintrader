# Work continuation

Version: 237
Delta: v236 to v237; record ten-second refresh implementation and independent acceptance.

## v237 - 2026-11-08

Implemented automatic ten-second prediction-read cooldowns in both Live views. The dashboard polls with Follow stream off while visible, retries failed reads, shows successful refresh times, suppresses obsolete coin/floor responses and admits only one read. The TUI reads in one background Textual worker, preserves graph responsiveness, applies coin/floor generation guards, reports failed reads and retries, advances only successful refresh timestamps and drains safely at shutdown. Both preserve saved closed-minute forecast issuance, quality floors, immutable tick scores and all training/execution paths. Extension version is 0.4.2.

Verified: 372/372 extension unit/parity tests; 12/12 focused TUI tests plus an expanded stale-success/failure regression; Chrome 24/24 real-host and 23/23 fixture-host checks; Mongo 34 tests with 17 server-dependent skips; positive offline grid round trip net $0.3492; public Jupiter endpoint checks; changed-source syntax checks. Independent real-clock Chrome and Textual acceptance observed automatic UP/DOWN/UP row changes and recovery after a failed fourth read. Ten-second cooldown plus one-second timer yielded approximately eleven-second start gaps. Each surface admitted only one reader. Hidden/disposed browser views stopped polling; held TUI reads kept the chart responsive and stale contexts were discarded. Existing user sessions and services were not restarted.

Delivery branch fix/live-predictions-10s-20261108 in /Users/mitch/dev/solmargintrader-wt-refresh-10s is the current checkpoint. Remaining gates at this checkpoint: rebuild offline indexes, repeat the backtester after index regeneration, final-head CI, merge, safe master sync and own worktree cleanup. The first backtester run passed 908 cases and failed only the expected stale-index assertion while files were still being edited. Documentation discovery is 1214 SolTUI / 2529 total. The full optional SolTUI suite was not run. On resume, use the branch's PR merged status and final-commit checks as the delivery receipt. Stele task create 0a351c54 and diagnosis knowledge 470f5f70 remain queued because MCP is unavailable.

## v236 - 2026-11-08

Target: refresh the Live graph forward-predictions table every ten seconds in the TUI and dashboard. The SOL store contains recent calls. Both views currently gate table reads at sixty seconds; the dashboard also requires Follow stream for polling and switches it off after a transient read failure. A saved snapshot read took 1.17 seconds, so move the TUI read to a single background worker with stale-coin/result guards. Keep retries visible and continue them after failures.

Preserve closed-minute forecast issuance and trainer evidence; do not edit forwardtest.py or historical results. Keep score floors, immutable tick history and all order paths unchanged. Worktree /Users/mitch/dev/solmargintrader-wt-refresh-10s; branch fix/live-predictions-10s-20261108; base 2ca3041. Shared checkout has three unrelated untracked guides and other active worktrees. Task create queued as Stele outbox 0a351c54 because MCP is unavailable. Remaining: implement, verify ten-second cadence and recovery in fresh UI instances, refresh docs/indexes, then commit, push, pass CI, merge and clean up.

## v235 - 2026-11-08

Aggregate live prediction score and minimum-voting-score work is implemented in both surfaces. PR https://github.com/mithudso/solmargintrader/pull/146 is the delivery receipt. The display uses shared policy vectors, equal strategy means, -100..100 scores, 20/60 label thresholds, 60% accuracy and 20 resolved eligibility defaults, actual latest-call expiry, and immutable right-anchored tick slots. These controls are separate from paper min_confidence=0.80 and do not change training/execution. No task diff touches forwardtest.py or simulation.py relative to the integrated default branch.

Final product acceptance passed: independent Chrome and headless Textual verified all five colors/labels, weak/sparse/stale/future exclusions, physical eight-column TUI movement, immutable history, missing-coin reset and obsolete success/error suppression. Integrated Python 106/106; extension 372/372; Chrome real-host 24/24 and fixture 23/23. The native installer regression passes after resolving the merge (its earlier error occurred while source still had conflict markers). Documentation counts are 1211 SolTUI and 2526 total. Full TUI suite remains optional and was not run.

Current head includes delivered paper-control PRs 142/145; both source and histories were preserved. Remaining delivery gates: offline documentation/index refresh, final backtester/index checks, final-head CI, merge and cleanup. No order, signing, trainer/service start, user configuration update or existing-profile reload occurred during verification. Shared checkout is owned by another live session; leave it intact. Stele task create queued as 2f9370e6; new bug lessons queued as f07021b5, 65b7724f, 9397d749. Earlier checkpoints are historical.

## v234 - 2026-11-08

Resumed the aggregate live score and minimum-voting-score request after interruption. Retained the checkpoint 947f311 and merged delivered PRs 142/145 without changing their fee/leverage/short/confidence behavior. Voting accuracy/sample floors remain display-only and separate from the owner-confirmed paper min_confidence=0.80. Worktree /Users/mitch/dev/solmargintrader-wt-live-score; shared checkout is active elsewhere and must not be touched.

Verified before integration: 372 extension tests, 15 focused Python/UI tests and 24 real-host /23 fixture-host browser checks. Independent review verified the physical eight-column TUI shift and found coin-switch stale state; those view-reset fixes are implemented. Remaining: guard obsolete browser failures, bind eligibility counts/accuracy to the same latest trial as its direction, rerun independent acceptance after merge resolution, refresh counts/indexes, push PR, wait for final CI and merge. Stele task create outbox 2f9370e6; decision writes a83639ac, dbd594d9, 5d4bb1e8.

## v233 - 2026-11-08

Owner added: strategies need a minimum prediction score to vote. Use saved live_vote_min_accuracy=60.0 and live_vote_min_resolved=20 defaults. Require both the strategy-wide forward record and the voted horizon to meet these floors; keep excluded rows visible. Controls in dashboard and Signal Live save through settings.save. Ratings remain informational agreement. Completed: backend snapshot with latest-call expiry; shared Python/JS policy vectors; both headers and immutable score tapes; 372 Node tests and 15 focused Python/UI tests passed before final browser-regression expansion. Remaining: independent acceptance, full relevant checks, documentation/index updates and PR delivery.

## v232 - 2026-11-08

Target: add the same aggregate signed score and five-level colored label above live-price and prediction views in the dashboard and TUI. Preserve each tick score as observed; append on fresh source ticks and scroll left with the plotted window. Worktree /Users/mitch/dev/solmargintrader-wt-live-score; branch feat/live-aggregate-score-20261108; base origin/master 2fc1845. Preserve the shared checkout untracked guides and other sessions. Stele task creation queued as 2f9370e6.

Plan: inspect the prediction and chart data contracts; implement one read-only backend aggregation plus matching score tapes; test Python logic, headless TUI and real Chrome; refresh docs/indexes and deliver through CI/PR/merge. No trading, training, worker starts or historical result rewrites.

Decision: use equal strategy weights. Within each strategy average its current UP=+1, DOWN=-1, FLAT=0 horizon votes; average strategies and multiply by 100. Ratings: Strong Buy >=60, Buy >=20, Flat between -20 and 20, Sell <=-20, Strong Sell <=-60. This is directional agreement, not an accuracy or success probability. Missing/stale/future-dated evidence produces an unavailable gray Flat instead of a made-up zero. Read actual latest call/expiry per strategy and horizon in a separate display module: do not edit forwardtest.py, whose whole-file hash partitions training evidence. Annotate only new recorder timestamps, with the score known then; never backfill cached prices with a later score.

## v231 - 2026-11-08

COMPLETED: Jupiter paper fee and execution controls delivered in https://github.com/mithudso/solmargintrader/pull/142 at squash cd4002806241d1315abf31e2d9660f2adbf9d73a (2026-11-09 02:30:23 UTC). All eight required CI jobs passed on final reviewed head 9e6b3b840a0be6e316542528fa2ea8670a400707. The remote merged tree exactly matched that head. The full SolTUI suite was not run; required mapped macOS tests and targeted integration checks passed.

Both Forwardtest and Backtest expose opt-in leverage and short DOWN positions, plus the owner-confirmed default minimum confidence 0.80. Jupiter Perps uses 6 bps per entry/exit on notional, with explicit borrow/slippage scenarios and isolated liquidation. Confidence uses prior resolved calls; unknown confidence blocks a trade. Short combinations require directional agreement, and confidence respects open/close fill timing. Forecasts continue even when paper trades are skipped. Histories and per-trial cost snapshots persist. No live trading path was added.

Local master was fast-forwarded to the merge. The two pre-existing untracked guides retained their hashes. The feature branch, remote branch and private feature worktree were removed. The installed /Users/mitch/.local/bin/soltui launcher returned jupiter-perps, fee_bps=6, min_confidence=0.8, use_leverage=false, allow_short=false, mode=dry-run, armed=false under isolated config. Fourteen regressions passed again from /Users/mitch/dev/solmargintrader. Fresh Textual checks covered 100/180-column controls. The already-open console was left running; no owner state was restarted.

No product work remains. This completion record ships through its documentation PR. Stele requests remain queued because this session has no Stele MCP: 470a5bc1, 93dc9fb7, f07325c1, cd0f7955, 58f42fcb. Treat earlier pending checkpoints below as historical and use PR 142 for the product delivery receipt.

## v230 - 2026-11-08

Integrated PR 144, which independently guarded the same compound row callback during tab switches. The combined handler preserves its active-tab condition and resolves both widgets before updating them. All fee, leverage, short and confidence behavior remains unchanged. Final CI must run against this integrated head before PR 142 merges. Other sessions are now back on master; only fast-forward a clean tracked checkout after delivery, preserving the two untracked guides.

## v229 - 2026-11-08

Confidence calibration now uses the prior decision close when fill_delay=0, and the delayed bar open when fill_delay>=1. A regression with rising open-to-close bars but unchanged consecutive closes proves that same-close entries cannot learn a false success rate from intrabar moves they did not own. Both paths settle only after the predicted bar closes. This preserves the minimum 0.80 gate and no-lookahead contract. Fourteen regression tests pass. PR 142 must pass final-head CI before merge.

## v228 - 2026-11-08

Short-enabled combinations now use directional agreement. The old Composite all=min rule could choose a short for contradictory +1/-1 members after enabling the MA bearish branch. The paper adapter now requires same-side unanimity for all, rejects conflicting any calls, nets signed vote counts, and preserves signed means. Each member runs once per visible bar. The regression covers mixed, bearish, flat and majority-short combinations. Long-only combination behavior remains unchanged. CI for PR 142 must validate this final correction before merge.

## v227 - 2026-11-08

Integrated extension dashboard PR 143 after final CI passed but before PR 142 could merge. Source changes do not overlap the paper engine. Retained all extension and Jupiter requests and continuation records, then recomputed documentation counts and offline indexes. PR 142 remains the delivery receipt; CI must pass on its new integrated head. The historical Gemini handoff is not current execution guidance.

## v226 - 2026-11-08

Retained the separate Jupiter order handoff from PR 135 while merging its records. That record states: Owner requested handoff to Gemini. PR 134 merged incomplete at 314fe989 while docs CI failed and SolTUI CI was pending; the previous agent did not merge it. TASK-1044 released for next agent. See /Users/mitch/dev/solmargintrader/JUPITER_GEMINI_HANDOFF.md for current state, verification, risks and remaining implementation. Jupiter order execution is not implemented. These order-execution gaps are separate from the paper-only Jupiter fee and confidence controls in PR 142.

Historical note only: the PR 143 record below corrects this earlier handoff checkpoint; consult current manual-order source and PR 137 before acting.

## v225 - 2026-11-08

Jupiter paper testing is implemented in simulation.py and shared by forwardtest, runner/CPCV, P&L curves, replay, F5 and new paper experiments. The owner confirmed 0.80; 1x long-only remains the default and leverage/shorts are opt-in. Existing forward evidence retains its original assumptions. Liquidation stops further paper entries for a wiped-out trial while forecasts continue. Borrow/slippage remain explicit scenarios; network/keeper/collateral-swap costs are excluded. Other assets use synthetic Jupiter economics.

Verified: 13 new accounting/no-lookahead/engine-parity/migration/layout tests; 25 forward tests; 70 F5/paper/P&L/dry-run tests; 85 helper/background tests; 164 mapped CI tests; 909 backtester tests; 361 extension tests; 34 Mongo tests (17 server cases skip without mongod); positive offline round trip; docs/index gates. Fresh Textual acceptance passed at widths 100 and 180. Integration fixed restored-plan controls before the first timer and a queued compound selection after widget removal. CI runner now isolates config so persistent/autostart tests cannot edit the owner's saved plan.

Delivery receipt: https://github.com/mithudso/solmargintrader/pull/142. This record ships with that PR; the PR's merged status and final-commit checks establish delivery. No product implementation remains. The already-open console is not restarted; the shared checkout and other sessions are preserved. Stele writes are queued as 470a5bc1, 93dc9fb7 and f07325c1 because this session has no Stele MCP. The private delivery worktree is /Users/mitch/dev/solmargintrader-wt-01a1bded.

## v224 - 2026-11-08

Integrated chart PR 141 without changing its signal/live behavior. Preserved each request and both continuation histories. Jupiter source and UI checks pass; final checks and delivery follow after refreshing generated counts and indexes. No change to the other session worktree or installed console.

## v223 - 2026-11-08

Implemented Jupiter Perps fee profiles, optional leverage/shorts, and owner-confirmed minimum confidence 0.80. Prior resolved-call confidence gates entries; no-lookahead tests cover fill delay. Each forward trial stores the cost/execution snapshot and each call stores confidence, eligibility and net return. Fees and borrow use full notional; intraminute liquidation forfeits collateral. P&L, CPCV, dry runs, F5 and new paper experiments share assumptions. Historical rows remain intact. Fresh Textual acceptance passed both forms at 180 and 100 columns, after fixing overflowing inputs. Initial keyword search auto-refreshed the already-dirty generated index in the shared checkout; no further writes there. Stele decision queued as f07325c1. Remaining: final tests and documentation/index checks, commit, PR checks and merge; existing installed console not reloaded because the shared checkout has another session and a pending merge.

## v222 - 2026-11-08

Scope: Jupiter simulation costs and forward/backtest controls for leverage, short DOWN calls, and minimum confidence. Private worktree /Users/mitch/dev/solmargintrader-wt-01a1bded starts at origin/master 8195771. Other checkout has a live session and unfinished merge; preserve it. Preserve historical evidence and causal signals; no new live execution. Stele task/decision queued as outbox 470a5bc1 and 93dc9fb7 because no Stele MCP is available and the recall agent runtime failed. Remaining: inspect calculation paths, implement consistent controls and provenance, test accounting and no lookahead, verify UI, commit and deliver through PR.

## v221 - 2026-11-08

Merged the historical Gemini handoff PR 135 while preserving the current extension continuation. Its imported note below describes an earlier PR 134 checkpoint. Current source already contains the Jupiter manual-order handlers delivered in PR 137; do not treat the old handoff as the current implementation state. Live venue submission remains outside this task's verification.

Imported historical note: Owner requested handoff to Gemini. PR 134 merged incomplete at 314fe989 while docs CI failed and SolTUI CI was pending; the previous agent did not merge it. TASK-1044 released for next agent. See JUPITER_GEMINI_HANDOFF.md for that earlier checkpoint.

## v220 - 2026-11-08

Extension dashboard parity 0.4.0 is implemented and locally verified. All 147 current SolTUI commands are accessible by workflow. Now shows automatic read-only process snapshots; Signal shows recorded prices and saved predictions; research, replay, bots, experiments/heatmaps, manual reviewed orders, wallets, documents/editor and settings use the same Python handlers. Confirmation resets on parameter/row changes and after attempts. Fresh previews override cached submit history; false values and explicit empty strings reach the backend. Optional untouched text remains omitted (caught by fixture-browser parity). Persistent native leases preserve runtime; long-call workers allow cancellation; timeouts never replay.

Final local results: 369 extension tests; 24 real-host Chrome checks and 23 fixture-host Chrome checks; 42 focused Python bridge checks; 909 backtester tests; Mongo 34 tests with 17 server-dependent skips; positive offline grid round trip net $0.3492; public Jupiter read endpoints pass; documentation counts and offline metadata/text/concept indexes checked. The full 1189-test SolTUI suite is optional and was not run. Independent browser acceptance also verified a real CSV download and document read. Mock-only browser writes exercise order handoff and editor conflict paths; no live order, signing, daemon restart or trainer start occurred.

Delivery receipt: https://github.com/mithudso/solmargintrader/pull/143. Read that PR for the final CI, merged state and squash commit rather than inferring them from this checkpoint. No additional product implementation remains. The shared /Users/mitch/dev/solmargintrader checkout belongs to other active sessions; preserve its branch and dirty TUI work. The owner's existing Chrome profile was not reloaded. Stele task and knowledge writes are queued under dcbde101, 17d6b326, 8a990cf6 and 867c033e because this session has no Stele MCP tools. Earlier pending-work entries below are historical.

## v219 - 2026-11-08

Dashboard parity PR: https://github.com/mithudso/solmargintrader/pull/143 (draft during final verification). Independent acceptance loaded Chrome 156 with extension 0.4.0 and all 147 tools. Actual CSV download, real document read, mock confirmation reset, explicit empty/false, preview handoff and editor conflict tests pass. The regression scenarios now live in extension/e2e/lib/dashboard-workspace.mjs and run inside the guarded real-browser gate. Extension: 369/369 unit/parity tests. Browser: 24/24 using real native host. Focused Python bridge: 42/42. Mongo: 34 tests, 17 skipped without server. Grid dry run closed one round trip net $0.3492. Public Jupiter endpoints reachable. Merged origin/master chart work and preserved both histories; current counts are 1189 SolTUI and 2501 total. Full TUI suite remains optional and was not run. Final offline index rebuild, final source checks, passing CI and PR merge remain. Shared checkout is active on another branch with unrelated dirty TUI work and must not be switched or overwritten.

## v218 - 2026-11-08

Merged current origin/master into the isolated dashboard branch without touching the active shared checkout. Preserved both tasks and prompt histories. Complete remaining verification and delivery on this combined tree.

## v217 - 2026-11-08

Extension parity implementation is complete in /Users/mitch/dev/solmargintrader-wt-01a1bdf1. Owner clarified dashboard-first usage. Added workflow navigation for all 147 installed commands, typed forms with false/explicit clear, structured sortable tables and CSV/JSON, live recorder chart/predictions, sparse experiment heatmaps and catalogued editor. Existing reviewed-order gates remain in Python. Native dashboard leases retain multiplexed runtime; bounded long-call dispatch permits status/cancel; auto-reload waits for dashboards. No call is retried after timeout/disconnect. Independent browser review caught and fixed stale confirmations and cached-preview replacement. Node suite passed 369 tests before the latest UI refinements; 42 focused Python bridge tests pass. Real-host browser gate passed 23 checks before the latest refinements. Backtester has one expected stale-index failure (909 total); rebuild offline generated indexes before final checks. Mongo: 34 tests, 17 skipped without mongod. Oscillating grid closes one positive round trip, net $0.3492. Stele task outbox dcbde101; knowledge outbox 17d6b326, 8a990cf6, 867c033e. Remaining: persist browser regressions, final verification, count/index documentation, push PR, passing CI, merge, remote content verification and cleanup. Do not switch or overwrite the shared active checkout.

## v216 - 2026-11-08

Target: full browser access to SolTUI tools through its shared registry, with usable workflow navigation, typed forms, tables/charts, CSV exports and document editing. Worktree: /Users/mitch/dev/solmargintrader-wt-01a1bdf1; branch feat/extension-tui-parity-20261108 based on origin/master. Shared checkout has active concurrent edits and MERGE_HEAD; do not touch it. Stele task creation outbox dcbde101. Recall specialist failed before execution because its fixed model is unsupported; MCP tools are absent.

Steps: inventory in progress; workspace and native-session implementation pending; browser/unit verification pending; documentation, CI and delivery pending. Native transport currently kills process-local replay/job state after each request. Persist the host only while dashboard leases exist, multiplex requests, and never retry ambiguous calls. Preserve install defaults, existing order gates and archived Aero status. No live transactions or worker starts are authorized as verification.

## v215 - 2026-11-08

TASK-1064: In SolTUI under Signal tab Live page (`cmp-live`), added `#signal-live-chart-yaxis` (High, Mid, Low price levels with vertical ticks) and `#signal-live-chart-xaxis` (Start, Mid, End UTC timestamps matching data points). Implemented strategy prediction scheduler in `_signal_live_tick()` running every 1 minute (60s) or on candle minute rollover, preserving table cursor and detail selection. Added unit tests in `soltui/tests/test_signal_live.py` (7 tests pass); synchronized test counts across doc suite (soltui: 1183, total: 2487). All suites and checks pass (`check_docs.py`, `npm test`, `backtester`, `mongo`, `dryrun.js`).

## v214 - 2026-11-08

TASK-1064: In SolTUI under Signal tab Live page (`cmp-live`), add timestamps and price numbers to the price chart. Schedule top-performing forward-test strategy predictions to update with incoming streaming prices from the pricefeed daemon or on a 1-minute cadence. Preserve read-only SolTUI guarantees and non-lookahead semantics.

## v213 - 2026-11-08

Executed repo-bootstrapper skill: audited against mdb-tam standard, generated canonical MIT LICENSE from owner defaults (~/.config/owner-defaults.toml), implemented scripts/rotate-workflow-logs.mjs, rotated 219 sections from memory.md into docs/archive/memory-2026-11-08.md (reducing memory.md from 277 KB to 12 KB), synchronized test counts across doc suite (soltui: 1176, total: 2480), verified index/build.py --check (2645 files match), verified check_docs.py (0 errors), confirmed all suites pass, and updated project registry in global-ai-hub. Generated audit ledger at docs/repo-bootstrap-audit-2026-11-08.md.

## v212 - 2026-11-08

TASK-1057: In /Users/mitch/dev/solmargintrader-wt-01a1bd6d, investigate forward-test data lost across restarts. Calls are committed to SQLite per asset tick, but the running plan and selected coverage exist only in memory, and fetched candles are not retained in the forward database. Preserve existing records and concurrent work. Implemented SQLite closed-candle retention before strategy processing and a saved running plan restored on console startup; explicit Stop clears the plan. Focused forward-test suite passed 23 tests. The docs count gate reports existing count drift (1163 versus 1155). Remaining: assess multi-process ownership, abrupt-shutdown and live installed-app restart; finish delivery.

## v211 - 2026-11-08

TASK-1044 continuation: fixed _docs_view_changed teardown NoMatches; previously failing test passes. Added Jupiter Tokens API v2 discovery command and UI search; rejects missing decimals, ambiguous symbols and unverified resolution, displays full mint. Five focused tests pass. Jupiter quote, on-chain mint checks, balance, fees, exact Swap v2 transaction verification, confirmed submission and reconciliation remain unimplemented; UI remains disarmed and labels Jupiter unavailable. The docs and backtester CI failures were stale generated index. Rebuild index after staging final files. Draft PR 134 remains open. No live transaction.

## v209 - 2026-11-08

TASK-1044: Implement Jupiter and Coinbase advanced orders on a dedicated Money page. Worktree /Users/mitch/dev/solmargintrader-wt-jupiter, based on origin/master ee75ba4. Owner confirmed previous task claim is stale. Preserve original untracked guide and other work. Guide has unsafe default decimals, zero valuation fallback, and unverified signing. Require exact mint and decimals, independent valuation, balances, exact transaction verification and explicit review; no ambiguous retry or unsolicited live order. Checkpoint: moved the existing advanced Coinbase ticket to a Money navigation view and updated UI tests. Jupiter remains unavailable; no token search, Swap v2 quote, transaction verification, signing, execute, or reconciliation has been implemented. Focused UI run completed: 23 passed and one errored during teardown in _docs_view_changed with NoMatches #docs-view; investigate. Draft PR https://github.com/mithudso/solmargintrader/pull/134. Remaining: fix and rerun tests, implement and test the full Jupiter path with semantic verification and ambiguity handling, then deliver and verify the loaded app.

## v207 - 2026-11-08

TASK-1051: Add CSV exports to all SolTUI tables and ensure editor save works. Worktree /Users/mitch/dev/solmargintrader-wt-01a1bd0d. Existing editor has guarded save; verify and improve discoverability as needed. Preserve read-only document restrictions and concurrent work. Implemented CSV export wrappers across main and modal tables, plus non-overwriting Downloads output. Existing editor save uses button, Ctrl+S and :w and retains the catalog guard. CSV tests and editor save/read-only tests passed; 19 experiment and bot editor tests passed. Remaining: delivery, CI, merge and fresh live acceptance.

## v206 - 2026-11-08

The first scheduled optimizer cycle failed triangle with `historical recorded evidence changed for USD-ADA-BTC:1794171600:1794175200`. It froze the hour while the recorder was still appending. Freeze only completed recorded hours and retain the fingerprint check so later changes to closed history still fail. Per-coin work continues independently. The running scheduler must be restarted using its own controls after delivery to load this fix. Stele lesson queued as outbox a9307950.

## v205 - 2026-11-08

Recurring bot optimizer PR 128 merged as d7010e63ba04b20fe77bfcb77dc1a7282f8250ed with passing required CI. The owner requested frequent per-coin tuning. A daily detached scheduler and dedicated launchd recovery watchdog have been started; verify their current status before reporting a run. The scheduler only adopts grid and DCA settings if the per-coin capability is present; triangle remains evidence-only. Stele transport was closed; leveraged-order verifier gap is queued as outbox 68fc7f6f.

## v204 - 2026-11-08

The user requested the advanced Money ticket and leveraged buys and sells. The user supplied /Users/mitch/dev/solmargintrader/jup.ag/coinbase_trading_reference.md. Its spot, regulated futures, and global derivatives describe distinct venues and eligibility. Use venue previews and verified account terms rather than static assumed fees or eligibility. The advanced ticket includes Coinbase market, limit, stop-limit and sell brackets, percentage sizing, a session price graph and forward-test forecasts. The venue preview estimates fees; final maker/taker fees depend on fills. The $100 per-order cap, balance reconciliation and single-submit journal apply. No live order was submitted in this work. Jupiter spot, leveraged longs/shorts and Coinbase derivatives remain unavailable until their venue-specific transaction verification, eligibility and reconciliation paths exist. Stele task creation is queued in outbox 5697c8bd.

Version: 146
Delta: v145 to v146; reconcile PR 96 source evidence with the catalog relocation.

Version: 143
Delta: v142 to v143; preserve concurrent delivery histories and source-card records.
Version: 145
Delta: v144 to v145; retain CI changes and editor work.
Version: 147
Delta: v146 to v147; correct test counts and record CI.
Version: 144
Delta: v143 to v144; preserve PR 100 records and resolve PR 104.

## v191 - 2026-11-08

The owner reports that the Forward Test table reverts the chosen column sort when the minute refresh redraws it. Preserve the chosen column and direction when new rows arrive. Stele task creation is queued in outbox b552278a because the transport closed. Implement in the active shortcuts worktree without interrupting forward workers.

## v192 - 2026-11-08

The optional 1082-test SolTUI suite on the Coinbase branch finished with eight failures and two errors. The strategy catalogue failures were stale expectations after PR 101 moved research and bot guides out of the executable cards directory. The catalogue test now verifies the relocated files without adding them to the queue. Stele lesson is queued as outbox bd3fb46a. UI help, title and glossary failures remain under investigation. The Coinbase feature passed its focused checks and required CI and merged in PR 125.

## v193 - 2026-11-08

The three full-suite UI failures now pass their focused tests after adding missing help, glossary entries, and four table titles. The relocated catalogue coverage tests also pass, with one unrelated skip. A complete suite rerun is still required. The F5 backend is being implemented separately as TASK-1046; it must not treat research-only guides as executable strategies.

## v194 - 2026-11-08

PR 125 merged at d945ac626d85d17f34b9391c21b4fc4df57a62b1 after required CI passed. The installed launcher returns the retained 928-pair Coinbase spot catalog; four headless interface tests passed with mocked orders. The already-open console predates the merge. The catalog task completion is queued as outbox a51dc1f8. Jupiter execution, F5 and live experiments remain unfinished.

## v195 - 2026-11-08

The owner requested optional manual entry for every Bots tab variable while retaining automatic defaults. They specifically want geometric versus arithmetic grid-order spacing available for comparison. Do not assume geometric spacing is more profitable; evaluate it on matching data and costs. Stele task creation is queued as outbox f2b957fa. Inspect each bot's configuration, backtest, forward and optimizer path so manual values are honored consistently.

## v196 - 2026-11-08

The owner requests independent bot optimization and configuration for every coin instead of choosing one shared configuration for all coins. Preserve separate evidence, saved settings and forward behavior per coin; do not overwrite unrelated coin settings. Stele task creation is queued as outbox ae3e15a1. The existing optimizer and configuration storage need investigation.

## v197 - 2026-11-08

The owner wants frequent, incremental per-coin auto-optimization and reports that any failed evaluation can block progress. Isolate unrelated failed candidate evaluations from the actual candidate comparison; keep negative valid results and require matched evidence for the candidate being adopted. Do not confuse a failed execution with a losing valid result. Retain the owner's ability to choose manual mode. Stele task creation is queued as outbox 5897ce13.

## v198 - 2026-11-08

PR 126 merged as 14c04d0f07e383bf4aeea2e8e77a3190dc4dfcf2 after required CI passed. It preserves Forward Test sorting, adds F8 strategy handoff, and documents Jupiter spot/perpetual cost differences. The complete SolTUI suite passed 1085 tests with two skips after the catalogue, help, glossary and table-title fixes. Two additional F8 Forward Test interaction tests also passed. The per-coin bot controls and optimizer remain under active implementation in this worktree.

## v199 - 2026-11-08

The owner asks the Experiments workbench Range, Stop and Step inputs to show defaults, clarify whether values are percentages, and offer percent adjustments beside the fields. These inputs describe the selected parameter's candidate values, not generally coin prices. The user was asked whether percentages should be relative to the current parameter value. Do not put a market price into a rung count or other non-price parameter. Stele task creation is queued as outbox baf0d624.

## v200 - 2026-11-08

F5 batch PR 127 merged as bb18a64fd2f52feae435680a22d0e8e1f81c3655 after required CI. Its detached runner freezes the eligible Coinbase USD spot universe and per-series proof, records missing, failed and unsupported cells, and starts independent forward trials using matching closed candle intervals. Existing cached histories may be incomplete; leveraged tiers remain unsupported and full-universe throughput is not measured. No production batch was started during testing. TASK-1046 remains to be closed after live acceptance.

## v201 - 2026-11-08

Per-coin bot tuning now separates confirmed results from tentative incremental adoption. Tentative adoption requires at least three matched holdout decisions, at least 80 percent matched coverage, a positive median and more wins than losses. Reports disclose that small samples are not statistically confirmed. Manual mode prevents automatic adoption. These bot workflows are simulation-only; a future live runner needs its own explicit risk policy. Stele decision queued as outbox a989c01c. Review identified aggregate skipped-coin reporting, holdout provenance and persistent confidence display issues; fixes and regression tests are in progress.

## v202 - 2026-11-08

The owner provided /Users/mitch/dev/solmargintrader/jup.ag/jupiter_defi_reference.md for Jupiter lending, fees and leverage. It lists perps base and variable fees, positions, liquidation and program identifiers. Its section 2.1 describes price-impact fees, while section 3.1 says standard fills have zero price impact. Current Jupiter documentation describes linear and additive impact fees, and Stele KNOW-813 flags a one-basis-point floor. Do not assume zero impact or trust program and fee constants without current venue verification. The owner also confirmed that experiment percentage controls should adjust the selected parameter's current value; display market price separately.

## v203 - 2026-11-08

Experiment range PR 130 merged as 514edb0651c5ba2c0c25e10f4dc44f6971c085ad after required CI. It shows selected parameter units, baseline defaults and relative percentage controls, with a separate fresh recorder quote when available. The owner confirmed parameter-relative adjustments. Headless installed-entrypoint acceptance passed; the existing console predates delivery. Stele decision queued as outbox 609e92e4.


## v204 - 2026-11-08

The owner requested adding a live page under the Signal tab in SolTUI that displays a price graph of the chosen coin, real-time subscribed streaming price information, and a table of top performing forward test strategies giving 1, 5, 10, and 30 min price predictions. Stele TASK-1063 was created and claimed under COMP-337. Stele decision queued as outbox 37afb21a. Implementation integrates `pricefeed.py` snapshot streaming, interactive `Sparkline` charting with mid-price history, and ranked strategy prediction evaluation across canonical horizons (1m, 5m, 10m, 30m) from `forwardtest.py` trials.

# Work continuation

Version: 218
Delta: v217 to v218; retain both chart and Jupiter continuation histories.

## v218 - 2026-11-08

Integrated chart PR 141 without changing its signal/live behavior. Preserved each request and both continuation histories. Jupiter source and UI checks pass; final checks and delivery follow after refreshing generated counts and indexes. No change to the other session worktree or installed console.

## v217 - 2026-11-08

Implemented Jupiter Perps fee profiles, optional leverage/shorts, and owner-confirmed minimum confidence 0.80. Prior resolved-call confidence gates entries; no-lookahead tests cover fill delay. Each forward trial stores the cost/execution snapshot and each call stores confidence, eligibility and net return. Fees and borrow use full notional; intraminute liquidation forfeits collateral. P&L, CPCV, dry runs, F5 and new paper experiments share assumptions. Historical rows remain intact. Fresh Textual acceptance passed both forms at 180 and 100 columns, after fixing overflowing inputs. Initial keyword search auto-refreshed the already-dirty generated index in the shared checkout; no further writes there. Stele decision queued as f07325c1. Remaining: final tests and documentation/index checks, commit, PR checks and merge; existing installed console not reloaded because the shared checkout has another session and a pending merge.

## v216 - 2026-11-08

Scope: Jupiter simulation costs and forward/backtest controls for leverage, short DOWN calls, and minimum confidence. Private worktree /Users/mitch/dev/solmargintrader-wt-01a1bded starts at origin/master 8195771. Other checkout has a live session and unfinished merge; preserve it. Preserve historical evidence and causal signals; no new live execution. Stele task/decision queued as outbox 470a5bc1 and 93dc9fb7 because no Stele MCP is available and the recall agent runtime failed. Remaining: inspect calculation paths, implement consistent controls and provenance, test accounting and no lookahead, verify UI, commit and deliver through PR.

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

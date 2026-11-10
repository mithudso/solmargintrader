# Task 4 independent review

Version: 1.1.0
Delta: 1.0.0 to 1.1.0; independently re-reviewed P1 remediation commit 170797f2a885a6e6780155c5fb16f5af24f1637d and report version 1.2.0. Prior findings retained below as resolved history.

## SPEC COMPLIANCE — PASS (reviewed source scope)

Both initial P1 findings are resolved in commit 170797f2a885a6e6780155c5fb16f5af24f1637d. Grid handles empty active segments. Manager execution has an explicit finite 2,048-bar lookback budget and at most 2,050 retained signal observations. Unsupported draft settings remain editable but execution refuses them without truncation. This is source acceptance; final package, full-suite, delivery and independent installed acceptance remain controller gates.

The reviewed implementation otherwise uses the canonical economic owners, preserves Grid geometry and attributed lots, DCA deal/safety/TP/cooldown state, next-open pending targets, global warmup and Trend hysteresis. The supplied 2,307-bar exact trade/equity/account parity fixtures cover all four families with JSON restart. Ledger segment insertion and input/checkpoint/fill publication share a transaction. Immutable segment bodies are digest chained; missing predecessors and fill-range mismatches refuse reads. Schema 5 requires segments and old schema-4 writers reject its version. Historical schemas remain readable without migration. Flat rebind hooks preserve the existing cash book and refuse unsupported position/history states. These are source-review conclusions, not independent installed acceptance.

## CODE QUALITY — PASS (no unresolved blocking findings)

### RESOLVED P1 — Grid crashes at an empty rollover boundary

Location: `/Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/strategies/grid.py:37`.

`data.get("origin_close", data["bars"][0]["close"])` evaluates the default expression even when `origin_close` exists. `rollover` legitimately produces an empty active `bars` list. When the next poll has no new completed bin (or stale/gapped source holds it), the worker explicitly publishes the unchanged account under the new segment, and `commit_progress` calls `validate_checkpoint`, which calls `run_identity` and `_configuration`. That path raises raw `IndexError: list index out of range`. It does not complete the atomic no-data transition or return a recoverable ManagerError. This is a normal polling condition, not corrupt input.

Independent reproduction: load the existing `tests.test_paper.recording` fixture with `load_recording`, save its first close in `origin_close`, set `bars=[]`, and call `grid._configuration(spec,data)`. The installed interpreter with worktree source returned `IndexError list index out of range` (exit 0 from the diagnostic wrapper). This exercises the exact failing constructor used during checkpoint validation.

Fix with an explicit conditional that reads the first bar only when origin_close is absent. Add a prospective worker test that reaches 512 bars, rolls over, receives no new completed bin, commits/restarts, and then resumes with the same account and immutable predecessor.

### RESOLVED P1 — Retained signal checkpoint grows with run length under accepted lookback extremes

Locations: `/Users/mitch/dev/solmargintrader-wt-01a1c447/backtester/core/engine.py:700` and `/Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/config.py:121`.

The engine retains `strategy.warmup_bars()+1` observations, while manager configuration accepts arbitrary positive `window` and `slow_period` with no upper bound. An accepted billion-bar lookback retains the complete observed prefix for years. Each continuation concatenates that full prefix, serializes it into the checkpoint, and archives another copy at segment transitions. Thus the advertised fixed active/checkpoint bound is absent across accepted configuration extremes; accumulated archives can also become quadratic rather than linear before warmup completes. The default-lookback test's 30 KB assertion cannot detect this.

Independent reproduction: both `resolve_config("momentum",{}, {"window":1000000000},None)` and Trend's equivalent slow_period override succeed. Repeated 128-bar `run_backtest(TsMomentum(1000000000),...,continuation=state)` calls retained 128 timestamps at cursor 128, 1,280 at cursor 1,280 and 2,560 at cursor 2,560. No broad suite was needed. Refuse unsupported lookbacks at manager admission with an explicit resource_limit and documented finite cap, or provide an exact canonical bounded state representation. Do not silently truncate indicators or alter timeframe.

## Additional observation

`RuntimeLedger._decode` walks and hashes every prior segment and compares every historical fill on every read. It uses bounded per-segment memory but cumulative read work grows with runtime age; `begin_tick`, commit, heartbeat and status can repeatedly incur this cost. This is not a separate blocker at the tested seven-day scale, but the claim of long-lived bounded resources should distinguish bounded active storage from unbounded history verification work. A future optimization must preserve chain and fill integrity rather than trusting an unchecked cache.

## Evidence and limits

Reviewed the exact brief, implementation report, scoped diff and current sources, including the continuation/rebind interfaces. Task 5 learning_adopt is outside this review. The supplied 45 focused, 116 economic and 19 load successes are author evidence; this reviewer did not rerun broad suites or install packages, write production state, start services, or touch trading capability. Two independent focused Python diagnostics above completed successfully and reproduced the findings. Full manager/economic final-head checks, coordinated package pins and installed continuation acceptance remain controller delivery gates. Product files were not edited.


## Re-review of remediation commit 170797f

The explicit Grid origin conditional avoids eager first-bar evaluation. Missing origin and empty bars now return recoverable input_unavailable. The new prospective regression drives the real worker/ledger transition at 512 bars, commits an empty waiting segment, verifies predecessor/account continuity, restarts and resumes at 513 with exact canonical fills/lots/equity. Its public data-check assertions use the active immutable specification despite a conflicting saved capital draft, prohibit strategy replay, and verify both database byte streams remain unchanged. Continued input cannot register as a fresh account.

`validate_runtime_config` rejects Trend slow_period and Momentum window above 2,048 before manager allocation/source capture. Since validated Trend fast_period is below slow_period, both Trend windows are bounded. Canonical warmup is unchanged: Trend retains slow_period observations and Momentum retains window+2. The guard covers input preparation, runtime registration/evaluation, direct start admission, research incumbents and candidate proposals, direct headless owner entry before temporal exposure, learned proposals and rebind. Stop still bypasses admission guards. Draft schema and standalone canonical offline engine support remain broad; no runtime clamps or synthetic history were introduced. The finite bound therefore applies to supported manager runtimes rather than every standalone backtester invocation, which is the intended component boundary.

Independent focused re-verification ran these three tests using the existing solbot interpreter and worktree PYTHONPATH:

- `test_grid_rollover_commits_empty_waiting_segment_and_resumes_same_account`
- `test_draft_extremes_refuse_before_runtime_allocation_source_research_or_adoption`
- `test_at_limit_manager_tail_and_checkpoint_stay_bounded_across_many_segments`

All three passed, final exit 0, in 2.091 seconds. At-limit coverage spans 4,353 bars over 35 segments and verifies retained tails never exceed 2,050 observations and serialized checkpoints remain below 400 KB for the fixture. The canonical metrics helper emitted an overflow RuntimeWarning for annualizing the short synthetic path; it did not alter test/account parity or the pass result. The reviewed report's 44 focused and 135 canonical/owner results remain author receipts; broad suites were not repeated. No product files, installed packages, production state or services were changed by this review.

The previously noted cumulative history-verification work remains a documented limitation, not a fixed-time claim or unresolved blocker. No additional spec or code-quality findings arose from this re-review. Task 5 automatic-learning correctness remains separately reviewed.

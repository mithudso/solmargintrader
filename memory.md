# Work continuation

Version: 204
Delta: v203 to v204; preserve recurring optimizer scheduler handoff.

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

## v1 - 2026-11-06

Active: repo-bootstrapper and code-deep-optimizer; Stele TASK-723.
Base: eebadbb5a937aa485825016650589bd5a4538b0d.
Worktree: /Users/mitch/dev/solmargintrader-bootstrap-cdo.
Branch: audit/bootstrap-cdo-20261106.

Completed: read instructions and continuation records; isolated existing research files and active dashboard-session-key worktree; read skills; began source and manifest audit. Semantic search returned unrelated repositories, so use source inspection. The configured Stele search agent cannot start on this account; direct MCP calls replace it. Recalled TASK-161 and KNOW-162 concern another project and do not guide this repo.

Constraints: dry-run/disarmed defaults; no guessed order amounts or fees; reconcile before plan; no automatic retry for ambiguous submissions; simulation only backtester; preserve liquidity caps and paused services; never read wallet key files.

Scope: optimizer default cap 50 prioritized files of 195 tracked Python/JS sources; full selected/remainder list in snapshot scope.json. Other source files remain outside this audit, not certified clean. No held-out benchmark: structural audit only, no empirical champion.

Snapshot: /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261106-bootstrap-cdo.

Remaining: baseline checks, finish bootstrap/code diagnostics, corroborate and fix findings, regressions and re-audit, update indexes and counts, commit/PR/CI/merge, verify remote SHA.

## v2 - 2026-11-06

Baseline commands and results:
- `/Users/mitch/.venvs/soltui/bin/python -m unittest discover -s backtester/tests -t .`: 651 pass.
- `/Users/mitch/.venvs/soltui/bin/python -m unittest discover -s soltui/tests -t .`: running.
- `/Users/mitch/.venvs/soltui/bin/python -m unittest discover -s mongo/tests -t .`: 20 tests, 17 skip without driver/server.
- `cd extension && npm test`: 162 pass.
- `cd extension && node tools/dryrun.js --ticks 8 --osc 6 --offline 100`: positive round trip, net $0.3492.
- `cd liquidity && PYTHONPATH=src /Users/mitch/dev/solmargintrader/liquidity/.venv/bin/pytest -q`: 351 pass, 6 network deselected.
- `cd liquidity && /Users/mitch/dev/solmargintrader/liquidity/.venv/bin/ruff check src tests`: pass.
- `cd liquidity && /Users/mitch/dev/solmargintrader/liquidity/.venv/bin/ruff format --check src tests`: pass.
- `/Users/mitch/.venvs/soltui/bin/python scripts/check_docs.py`: pass.
System python3 is 3.15 and lacks suite dependencies. Existing soltui venv is Python 3.13 with pandas/numpy/Textual, but no pymongo. No dependency install was performed.

Corroborated audit leads before implementation: engine ambiguous-submit retry, duplicate live-order collapse, exposure repricing, UTC-day loss reset, parallel ticks, persistent unknown fees. Executor topup drift gate, receipt-versus-state reporting, operation fund provenance and nonfinite execution settings. Full probe reports are in the snapshot directory and /tmp/solmargintrader-executor-audit.md. All source edits wait for diagnostics.

Upstream PR33 passed all CI and was merged by its owning session; origin/master now 7b9666f. Integrate that change before delivery. Preserve its session-key feature.

## v3 - 2026-11-06

Detailed optimizer scope is 17 risk-first sources across all six components. The earlier 50-file list was candidate triage; it was not 50 completed reviews. Snapshot scope.json preserves the candidate list, exact detailed scope and all 178 remaining source paths. Do not claim repository-wide CLEAN. This bounded scope allows complete verified remediation of the demonstrated execution/control defects.

Red-to-green so far: extension/test/risk-audit.test.js four tests; liquidity/tests/test_config_audit.py five tests. Root fixed risk normalization admission, order domains/count caps, numeric/shape validation in config.py/ExecConfig, and added liquidity/src/aero_lp/validation.py. Extension remediation owner audit_engine works engine.js/commands.js/risk.js and their tests. Liquidity remediation owner audit_executor works executor.py/engine.py and tests. Bootstrap owner finishes documentation/metadata. Do not overwrite parallel edits.

Remaining: finish other per-file diagnostics, corroborate/repair any new Medium+ defects, full suite gate and blind audit, source-only dossier, prompt/memory versions, indexes, Git delivery.

## v4 - 2026-11-06

Completed first remediation across 17 primary risk-first files and necessary dependencies. Full per-file initial findings and receipts are in /tmp/solmargintrader-*-audit.md and /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261106-bootstrap-cdo/. Added read-only semantic-verifier gate at Trigger adapter: bundled signer has no verified economic-intent bridge, so automatic live deposit/withdraw signing now refuses before raw signing. Dry-run remains supported. Never claim live acceptance or invent template support.

Root extras: HTTP writes never automatically replay; response-body read has deadline; secret-free transport diagnostics; API requires nonempty token, never prints it, masks upstream/body errors. Historical fill timestamps/cost evidence required; unknown fee/timing/carry holds new admission. Root fixtures red-to-green; core UNKNOWN-fill fixture now carries real timestamp.

First independent gate: liquidity2issues (late receipt mint orphan/retry; missing gas treatedzero) assigned audit_executor iteration2; extension4issues (context contamination, filledinventory excludedcap, arbitraryremote signing, belowentry boundedit) assigned audit_engine for3/core and root semantic-verifier gate forsigning. Independent simulation/TUI/Mongo/readout gate still running as blind_simulation. No final CLEAN claim yet.

Bootstrap metadata/docs owner completed37paths and audit ledger. Mongo/readout owner completed9findings with16regressions (pure/mocked, no actualDB calls). Background lifecycle specialist completed4findings with20regressions and explicit proof mismatch refusal + --results-path. No default history rewritten. First red fixture briefly wrote/unlinked defaultworker.pid before isolation; final observed /Users/mitch/.config/soltui/bg had only worker.lock, no runningworker/pid/state/results. Prior PIDfile contents cannot be proven. All subsequent fixtures use temporarypaths; no process was launched/signalled.

Checks sofar: full backtester666tests has only expected staleindexfailure; liquidity403offlinepass beforeiteration2; extension218pass beforeiteration2; background144targetedtests with1skip; historicalnumberchecker1084figures agree with archivedCSV (not re-derived underchangedengine). Jupiter keyless reachability and auth-routeprobe passed, keyedpricecheck skipped. No liveorders/RPC transactions, keys, installs, inference/indexing or serviceactivations occurred.

Stele transport closed during TASK-727 claim/complete calls; no acknowledgements. TASK-723 and TASK-728 closeout still pending. Use MCP only when restored; do not edit graph databases. Persist exact final delivery receipts here if unavailable.

Remaining: finish second remediation, rerun independentgates once (respect fiveiterationcap/two blindgate ceiling), source/docsintegration, merge upstream7b9666f session-keyfeature, updatecounts and generatedindexes, fullsuites/CI, commit/PR/merge/masterSHAverification, source-only externaldossier build. Prepared /tmp/smt-build-dossier.py (notrun); output /Users/mitch/.global-ai-hub/skills.llms/mithudso-solmargintrader.repo/; --no-probe-indexes --no-exec-inventory, no model jobs.

## v5 - 2026-11-06

Both blind review gates dissented. Stop independent reviews at the two-gate ceiling; final optimizer status stays BLIND-AUDIT-DISSENT. Final residuals: extension stop-after-writeahead race, missing cost basis, unbounded rungs; liquidity historical slot fee replay and stale reward snapshot. All received focused red-to-green regressions. First simulation residuals fixed too: IS-only triples, strict raw arrays/cadence, source-byte snapshots, proof-bound artifact inventory, authenticated worker Stop. No third independent review or full-repository CLEAN claim.

Current local checks: extension231pass; backtester681run with only expected staleindexfailure; soltui402run/1skip; mongo33run/17driver-serverskip; liquidity427pass/6networkdeselected plusRuffcheck/formatpass; offlinedryrun net+$0.3492/oneclosedroundtrip/no unknownfees. Mongo/report publish inventory proof and refuse legacyunprovenartifacts. No historicalresearchrerun.

Original master moved to9347b5b (PR33 dashboard session key and PR34 updated researchpackrouting). Preserve both; integrate before final delivery. Original five untrackedpaths unchanged; old dashboardworktree already removed by its owner.

Stele still returns Transport closed on TASK723fetch; complete TASK727/TASK728/TASK723 viaMCP only when restored. Local codecompletion is not a graphcompletionreceipt.

Remaining: commitcheckpoint, mergeorigin/master, finaldoccounts/offlineindexes/fullgates, pushdraftPR/CI/ready/squashmerge/sync, source-onlydossier/receipthashes. Exact deliveryreceipt path is the snapshot directory/delivery-receipt.json.

## v6 - 2026-11-06

Integrated upstream9347b5b without changing its session-key UI or gate-validated researchpackrouting. Source checkpoint9ff60e7; integrationc00c437. Final local gates: backtester681pass; extension237pass and syntaxpass; soltui402run/1skip; mongo33run/17driver-serverskip; liquidity427pass/6networkdeselected plusRuffcheck/formatpass; offline roundtrip net+$0.3492. Current docs count1353 across unittest+Node, separate liquiditypytest. Source-onlydossier preview emits11files/528cards/84deep/444shallow, caps/header/parity/pathchecks pass; final dossier must bind final mergedSHA. All35primary+dependency sources and189remaining Python/JS/MJS sourcepaths are enumerated in docs/code-optimizer-scope-2026-11-06.json.

Delivery state is authoritative in /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261106-bootstrap-cdo/delivery-receipt.json. If absent, remaining steps are generatedindexcommit, pushdraftPR, greenCI, ready/squashmerge, safeoriginalmasterff, removeonlyownedcleanworktree, source-onlydossier andreceipt. If present, use its PR/SHA/checks/preservation/dossier/remaining fields rather than repeating delivery. No sourceversions or historicalresearchfigures were arbitrarilybumped.

Optimizer final status BLIND-AUDIT-DISSENT. Bothgate residuals have focused fixes/regressions, not a third independentaudit. Scope and missingper-iteration-snapshot limitations remain explicit. LiveTrigger remainsblocked until trusted economic-intent verifier exists. Legacyunproven Mongo artifacts and changed worker history refuse; preserveoldhistory and choose a freshoutputpath. Liquidity may remainblocked after crash between durable journal and broadcast until externalproof resolvesoutcome; never infer notsent from missingreceipt. Singlewriter required for CLI/API file-backedstate; cross-processatomicity remainsuncertified. Archived research needsreruns before presentperformanceclaims. License and full five-standardopsinfrastructure remain separateowner/designchoices.

Stele TASK723/TASK727/TASK728 completion stillneedsMCP recovery (Transport closed); do not markcomplete withoutacknowledgement. No graphdatabaseedits.

## v7 - 2026-11-06

Final documentation now distinguishes current checks from historical extension receipts. It requires actual fill quantity, price, timestamp and cost basis. Incomplete history holds planning. The bundled Trigger signer cannot execute remote-crafted money movements without a trusted transaction-intent verifier.

The integrated source passes all available offline gates. The exhaustive source census has 224 Python/JS/MJS files: 17 primary audit files, 18 related dependencies and 189 remaining files. Passing regression tests do not certify those remaining files. The second independent audit dissented; focused fixes passed, but there is no third review or CLEAN claim.

Read the external delivery receipt before resuming. It records the final PR, merged SHA, CI checks, preserved paths, dossier hashes and remaining items. If that receipt does not exist, finish delivery using the v6 checklist. Graph closeout remains pending while Stele MCP returns Transport closed.

## v8 - 2026-11-06

Draft PR: https://github.com/mithudso/solmargintrader/pull/35 . First CI run42267344601 passed extension, backtester, liquidity and docs. Mongo reached its real server tests and failed `test_bars_is_a_native_time_series_collection` in mongo/tests/test_load.py:185 with `IndexError: list index out of range`. Its setup loaded only strategies/signals/indicators/documents. The corrected --only contract no longer creates unselected bars as an accidental side effect. CI now explicitly requests bars as well, so the native time-series assertion retains its full strength. No test skip or production selector rollback was added. Rerun CI before merge; receipt must bind the final passing head.

## v9 - 2026-11-06

Target: Stele TASK-775 (workstream M, EPIC-764). The live aero-lp daemon runs `liquidity/` in this repo, not `mithudso/aero-liquidity`.
Done in `liquidity/`: `aero-lp exit-to-safe` (dry-run default; live sets KILL; optional stable conversion off by default), `src/aero_lp/gates.py` (dry-run soak with fingerprint reset, one-time grandfather, research-gate block with logged owner override), CLI `gates` commands, daemon soak recording and `status.json` gates block, docs. The grandfather entry covers the soak only, not the research gate.
Verification: liquidity pytest 473 pass, Ruff check and format clean. Remaining: CI, merge, fast-forward the live checkout; the daemon is not restarted; write the grandfather record into `~/.aero-lp/soak.json` after merge.

## v10 - 2026-11-06

Target: DOC-754 workstream L, a real-browser end-to-end test for the extension. Branch e2e-real-browser, worktree /Users/mitch/dev/solmargintrader-wt-e2e. Stele MCP was unreachable (plugin:stele:stele failed to connect), so no task or knowledge node was written; record these facts in the graph when it is restored.

Completed: extension/tools/e2e.mjs (14 checks), extension/e2e/lib/cdp.mjs (DevTools-pipe client, Node built-ins only), extension/e2e/lib/guard.mjs (message allowlist; the harness cannot arm, sign, set mode, limits or keys), extension/test/e2e-harness.test.js (5 tests, part of npm test), npm script `e2e`, CI job extension-e2e, and the doc wording that said the unpacked load cannot be automated.

Facts to keep: branded Chrome ignores command-line extension loading, so the e2e needs Chrome for Testing or Chromium and CI downloads 156.0.8078.47 through pinned @puppeteer/browsers 3.2.6 (npx only, not a dependency). Extensions.loadUnpacked exists only on --remote-debugging-pipe with --enable-unsafe-extension-debugging. Dynamic import() is not allowed in a service worker, so modules are imported from the popup page. Files under a directory named test run under `node --test`, which is why the browser harness lives in extension/e2e/, not extension/test/.

Verification: four mutations each failed the e2e (default mode changed, missing-state rail made fail-open, API key leaked to storage.sync, price read changed to POST). Extension 242 tests; docs total 1358. No live order has ever been placed; the e2e verifies loading and dry-run only.

CI lessons from PR 39: (1) `python3 index/build.py all` indexes `git ls-files`, so build it after `git add -A`; built before staging it omitted the four new e2e files and CI reported "INDEX CHECK FAILED ... 4 added" in both the docs job and backtester test_index. (2) On Linux the service worker target is listed before its global scope exists: the first evaluate threw "ReferenceError: chrome is not defined"; the harness now waits for chrome.runtime. (3) rmSync of the Chrome profile can fail with ENOTEMPTY; cleanup now retries and warns.

## v11 - 2026-11-07

Target: SolTUI.app failed at launch with "A Python runtime not could be located". Branch fix/soltui-framework-python, worktree /Users/mitch/dev/solmargintrader-wt-soltui-runtime.

Cause: dist/SolTUI.app is a py2app alias build. Its Info.plist PyRuntimeLocations named only the python.org framework at /Library/Frameworks/Python.framework/Versions/3.13, which is no longer installed. ~/.venvs/soltui cannot rebuild it: that venv runs uv's standalone CPython, which is not a framework build.

Done on this Mac: created ~/.venvs/soltui-app on Homebrew python@3.13 (a framework build; pyvenv home /opt/homebrew/opt/python@3.13/bin), installed backtester and soltui requirements plus py2app 0.28.10, and rebuilt dist/SolTUI.app. PyRuntimeLocations now resolves to /opt/homebrew/opt/python@3.13/Frameworks/Python.framework/Versions/3.13/Python, a stable symlink across brew patch upgrades. The rebuilt app launched; the process loaded that framework and pyobjc from the new venv, with no error dialog. The broken bundle is kept in the session scratchpad.

Code: soltui-service build refuses a non-framework interpreter and fails when no PyRuntimeLocations entry exists after the build; status reports the runtime of each bundle. soltui/requirements.txt now lists py2app (darwin only). Docs: soltui/README.md, docs/INSTALLATION.md, docs/DEVELOPMENT.md.

Second fix, same branch: the Backtest tab's "Run Untested Sweep" button ran a bare `python3`, which now resolves to Homebrew 3.15 with no pandas, so `research/sweep.py` failed with "ModuleNotFoundError: No module named 'pandas'". The status line showed only the head of the traceback, which hid that line. soltui/tui.py now runs the sweep with `sys.executable` (untested_sweep_command), shows the end of stderr (failure_summary) and times out after 30 minutes. Running the script with ~/.venvs/soltui/bin/python completes (best untested strategy untested_macd, OOS Sharpe -0.027). The fetch hint in soltui/bgqueue.py still prints `python3 -m backtester.core.fetch`; it is only text to copy, and it is unchanged.

Remaining: none. ~/.venvs/soltui (TUI) is unchanged.

## v12 - 2026-11-07

Target: every TUI action available through the extension, CLI and API with one envelope, one access model and one call log (workstream P, branch feat/soltui-bridge).

Completed: `soltui/commands.py` registry (40 commands, dispatch, envelope, confirm gate on `liquidity.resume`, key-only call log); TUI rewired to dispatch; `soltui/cli.py`, `api.py`, `native_host.py`, `native_host_install.py`; parity, access, framing, logging and button-map tests (suite 449+); research/TOP_UNTESTED_RECOMMENDATION.json ignored as generated output.

Verification: full soltui suite, check_docs, live framed round trip and CLI-vs-API envelope equality on this Mac (see the PR).

Remaining: extension side (workstream X); restart Chrome after the first host install so it loads the manifest.

## v13 - 2026-11-07 (extension side)

Target: soltui command bridge, extension side. Branch ext-soltui-bridge, worktree /Users/mitch/dev/smt-wt-ext. Stele MCP was unreachable, so facts below are not yet in the graph.

Completed: `soltuiCommands` and `soltuiCall` in the registry (`extension/src/core/soltui.js`) over an injected `deps.soltui` transport; service-worker transport (`src/bg/soltui-transport.js`, `connectNative`, one short-lived port per request); node transport (`tools/soltui-transport.js`, same 4-byte framing); manifest `nativeMessaging` permission; dashboard SolTUI panel (`src/ui/soltui-panel.js`); 1-minute `solmargintrader-soltui-build` alarm and the reload gate (`src/core/autoreload.js`, `enginePending` in `engine.js`); fixtures `e2e/fixtures/`; tests `soltui-bridge`, `autoreload`, `soltui-parity`, `soltui-panel`; e2e extended (host manifest written into the Chrome for Testing profile's NativeMessagingHosts dir).

Facts to keep: (1) The owner's unpacked load path for extension pnokcppamfghgaimmmghoegjllhonhbh is /Users/mitch/dev/solmargintrader/extension, in Chrome Beta (`Google/Chrome Beta/Default/Secure Preferences`, `extensions.settings.<id>.path`). Branded Chrome (stable) has no entry. The installed permissions there are alarms and storage, so the owner must reload the extension once for nativeMessaging. (2) `chrome.runtime.reload()` fires onInstalled with reason update, and `handleInstalled` forces `armed: false` on every update, so an auto-reload disarms the grid; the kill switch and mode are kept. (3) The reload runs inside the engine store lock and holds it until the worker dies. (4) The soltui response is returned as `result` (the CLI prints it, the API nests it under `result`), never spread over the message response. (5) `test/surfaces.test.js` scans src/ui/*.js for the literal `type: '<word>'` as a message name, so UI code must set element kinds by assignment. (6) Fixtures live in e2e/fixtures, not test/, because files under test/ run under `node --test`.

Remaining: merge the origin/master Python side (done: PR 43), re-run the e2e against the production host, docs counts, CI, merge, fast-forward the live checkout.

## v14 - 2026-11-07

Target: owner request (prompts.md v8), read-only part only. PR A: Top 5 presets, net % everywhere, P&L tab. PR B: read-only wallet discovery. Branch soltui-pnl, worktree /Users/mitch/dev/smt-wt-pnl.

Completed (PR A): `soltui/presets.py` + `top5.presets` (Analyze, Live Run, Execute option lists; Execute and Analyze run the preset's composite with the SOL-tuned HORIZONS parameters; `paper.start` takes `top5:N`, `analyze.run` takes `preset`). `soltui/netpct.py`: net % = final / initial - 1, text always carries a source word. Net % added to Backtest, Top 5, Analyze, Cumulative, Execute, Live Run, Queue and Liquidity. `soltui/pnl.py` + `pnl.summary`, `pnl.series`, `pnl.breakdown` and the P&L tab: windows 24h/7d/30d/90d/ytd/all/custom, one section per source (backtest, paper, dry-run journal, dry-run/live LP), no total across simulated and real.

Decisions: backtest and paper windows are cut from the data's own dates, so a "30d" window ending today has no backtest data when the cached series ends earlier; the section says where its data is. The liquidity `status.json` is cumulative since open, so that section is marked not windowed; `ledger.sqlite` snapshots give a windowed history when present. The extension journal has no capital base, so it shows net $ and no %.

Not built (later, separately gated): swaps, signing, the live-run button, any private-key field.

## v15 - 2026-11-07 (leverage tiers, PR 1)

Target: low/medium/high margin tiers (2x/5x/20x) as Jupiter-Perps wrappers over the existing strategies, with intrabar liquidation; then the reliable-trigger miner (PR 2). Simulation only. Stele MCP was unreachable; facts below are not yet in the graph.

Completed: `IntrabarLayer` and `EngineConfig.intrabar` (finer 1m/1h bars walked inside each held bar; daily low/high still checked, never less severe); `CostConfig.liquidation_penalty_bps` and `liquidation_forfeits_collateral`; `backtester/core/leverage.py`; registered `lev_low`, `lev_medium`, `lev_high` with cards; `BlockResult.liquidations`; `research/leverage_tiers.py` and `research/LEVERAGE-TIERS.md`; `backtester/tests/test_intrabar_liquidation.py` (8 tests).

Result (SOL daily, CPCV, 514 paths): P(ruin) 1.2% / 21.0% / 73.7% / 95.3% at 1x / 2x / 5x / 20x; median OOS Sharpe -0.39 / -0.45 / -0.49 / -1.57. High leverage is ruinous.

Facts to keep: the engine already checked bar low/high, so intrabar layers refine ordering and fee timing and catch daily/hourly feed disagreements; SOL_1h covers only 366 days and has gaps (engine refuses a gapped series, so tiers are daily-only); decide/signal_redundancy/sweep_untested skip family leverage-tier.

Remaining: PR 2 (research/triggers.py, RELIABLE_SIGNALS.md, trigger strategy); follow-ups: soltui Triggers view, live trigger alerts through the executor.

## v16 - 2026-11-07 (reliable triggers, PR 2)

Target: mine conjunctions of causal conditions for out-of-sample directional reliability, report honestly, and trade the best candidates through the PR 1 tiers. Simulation only. PR 1 merged as 6a1b2dc (#44).

Completed: `backtester/core/trigger_conditions.py` (49 causal conditions, shared by miner and strategy); `research/triggers.py` (python3 -m research.triggers --asset SOL --interval 1d|1h; 13,510 daily and 30,720 hourly hypotheses, exact binomial vs base rate, BH FDR 5%, z>3, 30-event floor, purged/embargoed fixed split, stability, cross-asset replication); `research/trigger_backtest.py`; registered `trigger_trade` with card; `research/RELIABLE_SIGNALS.md` and results CSV/JSON; `backtester/tests/test_triggers.py`.

Result: no trigger qualified as reliable on SOL daily or hourly. Hourly cannot qualify (no hourly history for other coins to replicate on). Near-miss backtests are exploratory and ranked by discovery p-value, not validation results.

Facts to keep: the CI e2e (extension real browser) is flaky once ("installed mode: expected dry-run, got undefined"); a rerun passed. soltui tests iterate REGISTRY, so wrapper families (leverage-tier, trigger) need a FAMILY_NOTES entry and are excluded from the Signals-tab map test.

Remaining follow-ups: a soltui Triggers view over research/results/triggers_*.csv; live trigger alerts through the executor.

## v17 - 2026-11-07

Target: the owner reloaded the unpacked extension from /Users/mitch/dev/solmargintrader/extension and saw "no change": the version still read 0.1.0. The code on disk had changed (PR #42 added the nativeMessaging permission and a SolTUI panel), but nobody bumped the version, and the new panel is on the dashboard, not the popup.

Done: manifest.json and package.json are 0.2.0. The popup header and the dashboard title show the manifest version. The popup gains a "SolTUI console" button that opens dashboard.html#soltui. test/version.test.js keeps the two version fields equal and checks that both pages render the version. The CI extension job fails a pull request that changes extension/src or manifest.json without a version bump.

Owner steps (Chrome Beta, where the extension is installed): quit and reopen Chrome Beta once so it reads the com.mitchhudson.soltui native host manifest, then reload SolMarginTrader in chrome://extensions. The popup should then read v0.2.0.

## v18 - 2026-11-07 (executor, workstream E1)

Target: new component `executor/` for swaps between coins with best pricing; the foundation for a later "run this strategy live" button (E2 builds the runner and the button). Branch executor-e1, worktree /Users/mitch/dev/solmargintrader-wt-executor. Stele MCP was unreachable, so the facts below are in the outbox, not yet in the graph.

Completed: Python 3.13 package with uv lock, ruff and pytest (202 offline tests, 5 `-m network`); Jupiter Swap v1 quote/swap/price with an independent price reference; quote-only LI.FI cross-chain price; semantic transaction verifier (`txverify.py`, two layers, plus a re-simulation of the exact signed bytes); rails, per-strategy dry-run soak, mandatory research gate with a logged override; append-only journal with `unknown` handling and `reconcile`; CLI and loopback HTTP API over one registry with one envelope; `executor` CI job; root CLAUDE.md and docs now say seven components.

Facts to keep: (1) Jupiter now marks Swap API v1 "no longer actively maintained, superseded by Swap V2"; the owner chose v1. `lite-api.jup.ag` works keyless but returns 429 on a second call inside about a second, so the client spaces calls. (2) `priceImpactPct` is a fraction ("0.001078" at 20,000 SOL = 0.108%). (3) A simulated post-state includes the fee; `simulateTransaction` with `accounts` returns the post-state of every writable account, which is what the verifier compares. (4) The wallet held no USDC, so the live round trip ran sell first (SOL to USDC, then back). (5) Config comment lines contain the text `mode = "live"`: edit the config with a line-anchored replace, not a string replace.

Live validation (root CLAUDE.md conditions): reserved strategy `path-validation`, enabled only for the run, then switched off. Leg 1 SOL to USDC 0.011 SOL: 44MrREewJMLguLRw3pfMs5V3K1wFXRyxuD6pGDa5Kp1TWUWSd9TGiu9wTJ4ACYLFbqSe8WHMaLyBRDu8GvhHaYSS. Leg 2 USDC to SOL 0.99 USDC: 5veG62YXWFjX1XYeAzadLpaZ1MwaWd89dcwGt8Sjv6oS7uk1yscZKd1ggqBDFfugzP19yXc7EWB8DCao8FnpUSFH. Net cost of the round trip 51,110 lamports (about $0.005) and 47 raw USDC of dust; both post-trade checks passed.

Remaining: E2 (runner, soltui button); cross-chain execution; Swap V2 decision; owner to review the `path-validation` reserved strategy.

## v18 - 2026-11-07

Target: PR B of the read-only request (prompts.md v8): wallet discovery. Branch soltui-wallet, worktree /Users/mitch/dev/smt-wt-wallet. PR A (presets, net %, P&L tab) merged as d402b27.

Completed: `soltui/wallet.py` (public reads only: Solana getBalance / getTokenAccountsByOwner under Token and Token-2022 / stake getProgramAccounts, Jupiter keyless token and price APIs; Base eth_getBalance / eth_call balanceOf / position-manager NFTs, DefiLlama then DexScreener prices); `portfolio.scan` and `wallet.key_sources` registry commands; Settings gets the two public addresses (pre-filled with the owner's) and a read-only signing-key row (stat only, mode 600 check, files never opened); Wallet tab; a separate `wallet (live)` section in the P&L tab built from `~/.config/soltui/wallet-history.jsonl` (one line per scan; value change between scans, not trading P&L).

Findings: Blockscout answers 403 (Cloudflare challenge) to scripts, Routescan does not index Base, and public RPCs cannot enumerate tokens, so Base token discovery checks a built-in list, the daemon's ledger tokens and caller-supplied addresses, and says an uninvited token cannot be found without an indexer. Jupiter's keyless APIs return 429 when called back to back, so the transport paces each host and retries twice.

Safety: no field accepts private-key text; no key file is opened, read, hashed or printed; the scan sends no transaction and calls only balanceOf, symbol, decimals, name and tokenOfOwnerByIndex. Airdrop-looking tokens are flagged and excluded from totals.

Not built (later, separately gated): swaps, signing, the live-run button.

## v19 - 2026-11-07 (Coinbase account MCP setup)

Target: connect Coinbase account MCP for Codex. Source: https://coinbase.com/skill.md and https://docs.cdp.coinbase.com/coinbase-for-agents/skill.md (retrieved 2026-11-07).

Completed: read setup guide and metadata; no existing coinbase server. Task TASK-794, decision KNOW-796. Use the documented Codex remote OAuth flow and all ten advertised mcp scopes plus offline_access. Do not install a reusable skill automatically. No transaction or paid data request is authorized by setup.

Worktree: /Users/mitch/dev/solmargintrader-wt-01a1b575, branch agent-01a1b575. Original checkout has another live session and six unrelated untracked paths; preserve it.

Remaining: configure server, complete user OAuth, verify exposed portfolio-list tool, then commit/PR/CI/merge continuation records. Credentials stay in the harness credential store.

## v20 - 2026-11-07 (Coinbase configuration and OAuth result)

Completed: `codex mcp add coinbase --url https://agents.coinbase.com/mcp` added the global server in /Users/mitch/.codex/config.toml. Native OAuth returned `Successfully logged in.` with all ten advertised MCP scopes and offline_access. `codex mcp get coinbase` confirms enabled streamable_http at the exact endpoint. `codex mcp list --json` confirms enabled=true and auth_status=o_auth. The harness owns credential storage. No reusable skill installed.

Verification: the live-acceptance-verifier independently confirmed server configuration and OAuth status. This session and the verifier expose no Coinbase tools or native MCP reload tool. Account access is therefore unverified. Do not replace the harness with raw authenticated HTTP or extract credentials. The read-only portfolio-list call must succeed after reload before claiming verified access.

Repository checks: scripts/check_docs.py passed (703 backtester, 305 extension, 33 mongo, 597 soltui tests discovered). Regenerate the three offline retrieval indexes for the two workflow files and run index/build.py --check plus git diff --check before delivery. No product code changed.

Remaining user step: reload Codex to load Coinbase tools. Then call exposed coinbase_portfolios_list with empty arguments, without printing account details, and complete setup task TASK-794. TASK-795 tracks delivery of these records through CI and merge. No trades, transfers, paid requests, wallet-key access or service restarts occurred.

## v21 - 2026-11-07 (CDP CLI setup verification)

Target: verify the CDP CLI setup using https://docs.cdp.coinbase.com/cdp-cli/skill.md (retrieved 2026-11-07), separate from Coinbase account OAuth MCP.

Observed before changes: /opt/homebrew/bin/cdp version 2.0.145; Node v26.13.0; live environment already configured with wallet indicator. Preserve existing keychain configuration. The downloaded API-key JSON and wallet-secret text are untracked. They were mode 644; restrict them to mode 600 without reading contents or committing them.

Task: TASK-797. Worktree /Users/mitch/dev/solmargintrader-wt-01a1b575 at origin/master 7770e64; preserve original shared checkout and other active sessions.

Remaining: independent read-only cdp evm accounts list verification, final continuation update, offline index refresh, checks, commit/PR/CI/merge. No wallet creation, faucet, trade, transfer, or signing operation is required.

## v22 - 2026-11-07 (CDP CLI verified)

Result: existing CDP CLI setup passes the official guide. Independent live-acceptance-verifier ran /opt/homebrew/bin/cdp evm accounts list at 2026-11-07T10:18:45Z. Exit status was 0. Output was valid JSON with an accounts array containing zero entries and no error. cdp env returned live plus wallet indicators. Executable resolves to /opt/homebrew/lib/node_modules/@coinbase/cdp-cli/dist/index.js, version 2.0.145; Node is v26.13.0. No installation or credential replacement was needed.

Changed outside Git: /Users/mitch/dev/solmargintrader/cdp_api_key.json and /Users/mitch/dev/solmargintrader/cdp_wallet_secret.txt permissions changed from 644 to 600. Contents were not read, displayed, copied or committed. Existing CLI configuration was preserved. No account was created or funded. No transaction, signing or paid request occurred.

Checks: scripts/check_docs.py passed (703 backtester, 305 extension, 33 mongo, 597 soltui discovered); git diff --check passed. Refresh the three offline retrieval indexes for the workflow records and verify index/build.py --check.

Remaining setup steps: none for the CDP CLI. The separate Coinbase account OAuth MCP still needs a Codex reload and exposed portfolio-list call (TASK-794). Delivery for this request: commit only workflow records and offline indexes, PR, wait for all CI, merge, verify remote files and remove the private worktree. Preserve the active shared checkout and unrelated files.
## v23 - 2026-11-07

Target: prompts.md v10. Branch feat/wallet-xpubs, worktree /Users/mitch/dev/solmargintrader-wt-wallets.

Completed: `soltui/hdwallet.py` (BIP32 public derivation, Base58Check, bech32, private-key refusal), `utxo_scan.py` (BTC/LTC/DOGE, gap limit 20, P2PKH/P2SH-P2WPKH/P2WPKH), `eth_scan.py`, `spot_prices.py` (Coinbase), `portfolio.py` (snapshots, changes, notice), `portfolio_agent.py` (hourly LaunchAgent com.mitchhudson.soltui.portfolio); Settings fields, redacted on every surface, config file mode 600; commands wallet.addresses, portfolio.snapshot, portfolio.changes, portfolio.notice; TUI and menu-bar notice; extension 0.2.1 "Use soltui Solana address" button. The owner's identifiers are only in the local config, not in this repository.

Verification: soltui suite 669 tests, extension 313, check_docs agrees. Derivation checked on BIP32 vectors 1 and 2 and the BIP84 zpub vector. Live scan: Dogecoin read partial (BlockCypher 429); Base token discovery is partial (Blockscout blocked).

Remaining: none for this request beyond the open partials above.

## v24 - 2026-11-07 (Grid results and SolTUI help)

Target: answer grid profitability from saved results, distinguish exposure grid from resting ladder, and expand hover help across all fifteen SolTUI tabs with plain definitions and examples. Tasks TASK-799/800/801. Private worktree /Users/mitch/dev/solmargintrader-wt-help-01a1b575, branch feat/soltui-help-01a1b575 at ad6fe08. Preserve shared dirty checkout, unrelated worktrees, wallet files and live daemon. Existing glossary only covers headers; Queue and Liquidity tables bypass it. Add cell hover, specific controls/settings help, and F1 scrollable/searchable definitions. Archived grid CSV/card is from August and predates November engine corrections; verify data before claiming current profitability. The stele-search agent failed because gpt-5.4-mini is unsupported with this account; read its installed instructions and fetched named nodes directly. Remaining: validate results, implement help, UI regression and live acceptance, documentation/index updates, commit/PR/CI/merge.

## v25 - 2026-11-07 (Grid evidence and SolTUI help accepted locally)

Completed: fresh resting-ladder runs on engine ad6fe083 and the existing 1,875 daily SOL bars (2021-06-17 to 2026-08-04). research/results/grid_review_20261107.json binds configuration, costs and data SHA256; research/GRID-REVIEW.md explains it. Static account return +32.10% on USD144 (net USD46.23) versus holding +88.10%. Eight independent reset/close periods: five positive, median full-account +7.67%, worst -34.92%. These are period returns, not annual/monthly or a continuous recenter strategy. Costs are 6 bps fee plus 2 bps slippage per fill, about16bps per roundtrip; zero unborrowed spot carry. USD72 is a nominal rung budget, not measured deployed equity. Independent research-contract-auditor reproduced all9runs and accepted the report. The archived August CSV predates accounting fixes; qualified its card and graph note KNOW-642, and recorded KNOW-803.

Help: soltui/help.py centralizes plain-language terms, every displayed signal parameter, controls/settings and all15tabs. GlossaryTable now explains headers and actual cells, recognized strategy rows and context-specific kinds; Queue/Liquidity tables use it. soltui/help_screen.py supplies F1 searchable/scrollable help with focus return and plain-text rendering. Persistent hint tells users how to discover it. Existing dry-run, worker, editor, wallet and liquidity controls are unchanged.

Verification: focused10tests passed, final7newfunctionaltests passed, fullSolTUI676tests passed with1skip in341.573seconds. Tests exercise everytab/control/column, realcellhover/leave, allsignalparams/LPcolumns, overloadedkind, F1frominput/table, searchnomatch, scroll at80x24 and focus/value preservation. Ruff on newmodules/tests and whitespace checks pass. research/verify_numbers.py verified1084archivedfigures (a transcription check, not a current-engine performance gate).

Independent live-acceptance-verifier opened isolated textual-serve browser, confirmed visiblehint, actualfeebpshover example, F1gridsearch, PageDownscroll and Escapereturn. Frozen SHA256: tui a86e9636e34464138db113e0eb441cc1bfa2278abf13ca7ec2d0eb7d2cb92e75; help89868eae429c70eb39416f31ed5376a21a649fd5a485a6ac1720b0f53da8b2b6; help_screen82f1a1f4794b0afdd7f9e534478e55b93e9decb77f68bf330297a9e21015a8bb. Its server/browser areclosed; existing userTUI PID65485 waspreserved. Screenshots are outsideGit under /var/folders/hz/s7btlxx54c32yt375m03q0h40000gn/T/soltui-help-live-fk3gu963/screenshots/.

Remaining: commit source/docs so check_docs can discover newly committed testfile; regenerate/check offlineindexes; finalPR/CI/merge and remotecontentverification. Then sync default checkout only if safe and open a fresh console to load new code, preserving any old console draft. No filter, recenter, execution or live-profitability improvement was implemented or claimed. TASK-801 tracks delivery.

## v26 - 2026-11-07 (tradingstrategyresults.json coverage)

Target: check every strategy, signal and indicator in tradingstrategyresults.json against the registry, cards and soltui; add cards and queue entries for gaps. Stele TASK-804. Worktree /Users/mitch/dev/solmargintrader-wt-strategy-coverage, branch feat/strategy-coverage-tsr.

Found: 8 strategies and 13 indicators. Covered already: HODL (buy_and_hold), trend (ma_crossover), arbitrage (triangular_arbitrage and dex_cex_dislocation, spec-only), SMA, RSI, MACD, Bollinger, Stochastic, OBV, ATR, Ichimoku, VWAP. Missing: DCA, EMA and golden cross, PPO, Fibonacci retracement, swing trading, day trading, scalping, event-driven.

Completed: backtester/core/strategies/textbook.py (dca, ema_crossover, ppo, fib_retracement, swing_confluence) with indicators.ppo and indicators.fib_level; five `implemented` cards (so the soltui queue picks them up through bgqueue) and three spec-only cards (day_trading, scalping, event_driven). soltui: SignalDefaults fields, STRATEGY_PARAM_MAP, SIGNAL_GROUPS, validation, reference rows and help text. research/decide.py got a PPO indicator row. Tests: backtester/tests/test_textbook_strategies.py (31) and soltui/tests/test_tradingstrategyresults_coverage.py (6, checks the map against the catalogue file when present).

Verification: backtester 734 pass, soltui 682 pass, check_docs agrees, index check passes. Smoke numbers on SOL daily (single 70/30 split, default params) are in each card and are labelled as not sweep rows: all five lost money out of sample except swing_confluence (-7.5%, Sharpe 0.019). The queue will produce the evaluated numbers.

Remaining: PR, CI, merge. tradingstrategyresults.json itself stays untracked (the owner's source file).

## v27 - 2026-11-07 (Strategies tab test history and backtest buttons)

Target: Strategies tab shows whether each strategy was tested, how many times, when and the result; three buttons Backtest selected, Backtest all untested, Backtest all. Stele TASK-806, worktree /Users/mitch/dev/solmargintrader-wt-strategy-status, branch feat/strategy-test-status.

Completed: JobResult.finished_at (0.0 = pre-field row, shown as "date not recorded"); bgqueue.strategy_history/StrategyHistory/format_when (duplicates collapse by job_id, headline is the card's own parameters, never the best variation); build_queue(strategies=) and bgworker/bgcontrol --strategies; registry commands strategies.history and queue.backtest (scope selected|untested|all, tier 0, refuses cleanly when a sweep is running or nothing is pending); Strategies tab columns tested, times tested, last tested, card-preset result updated in place when the results file changes, three buttons, help text. Tests: test_strategy_history.py (25) and test_strategies_tab_history.py (5).

Verification: backtester 734, soltui 712 pass. Caveat: the worker refuses rows whose evaluation proof (code, data, settings hash) differs, so after a code change old results need a fresh results path; history still lists them with their date.

Remaining: PR, CI, merge. Next request (TASK-807): keyword/semantic/hybrid search over all repo files with mxbai-embed-large, ollama auto-start, idle indexing, lazy-loaded Docs-tab search.

## v28 - 2026-11-07 (Repo index tooling and Docs-tab search)

Target: keyword + semantic indexing of all repo files with mxbai-embed-large:latest, ollama reachable-or-started when semantic search is chosen, an idle index check that starts its own rebuild, and keyword/semantic/hybrid search in the Docs tab, lazy-loaded. Stele TASK-807, worktree /Users/mitch/dev/solmargintrader-wt-repo-search, branch feat/repo-search-lazy.

Found: index/build.py already built BM25, concept and mxbai-embed-large semantic indexes over tracked files; the committed semantic manifest was stale (246 files vs about 620). Not covered before: .mjs, .sh, .toml, .example (now indexed); .csv bodies stay excluded by design (header only); untracked files are outside "the repo" by the existing definition (git ls-files).

Completed: index/ollama_ensure.py (localhost only, starts the Ollama app or `ollama serve`, never pulls unless --pull); index/idle.py (rebuild only when stale AND idle AND unlocked AND model installed, nice 19, 10 minute throttle, writes only gitignored semantic-local.npz/json, INDEX_NO_AUTO=1 disables); search.py run_query() library API with lazy cache and unload(); build.py shared model constant, atomic writes, --local, --pull; registry commands docs.search and docs.search_unload; Docs-tab search box, mode select, Search and Free search memory buttons, nothing loaded until first search; CSS fix for the clipped Docs kind selector; removed four stray *.md-E files. A real local semantic build embedded 7,446 chunks in 187 s.

Decision: the committed keyword index is not rebuilt by the idle job (a 12 MB tracked file on a timer would keep every checkout dirty); search reports when it is behind and `build.py all` plus CI `--check` remain its gate.

Tests: test_index_search_tooling.py (32), test_docs_search.py (10). Verification: see PR.

Remaining: PR, CI, merge; build the semantic index in the main checkout after merge.

## v29 - 2026-11-07 (Prediction markets card)

Target: "Add looking at the prediction markets as another item to consider." Read as an addition to the strategy catalogue. Stele TASK-817. Added backtester/strategy_cards/prediction_markets.md: spec-only, family event, very-low a-priori, two ideas kept apart (odds as a signal for SOL; the markets as a venue: cross-venue mispricing and calibration bias), data gap named (price history and resolution outcomes, including the resolution-time lookahead trap), legal and venue access flagged as open questions. No code, not queued. soltui coverage test lists it as an extra card.

Also recorded: a side note that the five new strategy cards rest on one SOL daily 70/30 split, which RANKED_LISTS.md calls structurally hostile to long-only rules. The cards are implemented/very-low, not measured; use the soltui queue's sweep output, not the card numbers.

## v28 - 2026-11-07 (compound five-minute scorecard)

Target: score every metric in 5minleveragestrategies.json (plus higher timeframe, positioning, BTC lead, lifecycle, news/event/cost/liquidation gates) for the next 5m bar, aggregate to UP/DOWN/FLAT, and test any selection backward (engine, IS/OOS) and forward (live ledger) from a soltui tab with every item toggleable and every number editable. Stele TASK-815 (decision KNOW-816). Worktree /Users/mitch/dev/solmargintrader-wt-e63b4616, branch feat/compound-5m-signal.

Completed: backtester/core/scorecard.py (30 components, family dedupe, regime weights, gates, forecast stats, prefix-invariance tested); backtester/core/compound.py (5m loader, segments at gaps, PrecomputedTargets through run_backtest, variants grid, leaderboard with evidence floor); soltui/compound.py (config, Coinbase/Hyperliquid/RSS public reads, forward ledger, sweeps, CLI signal/forward/status/backtest/results/sweep/catalog); nine compound.* registry commands; Compound 5m tab; research/full_suite.py; skills/five-minute-signal (live copy ~/.claude/skills/five-minute-signal); docs/COMPOUND-5M.md.

Verification: backtester 802, soltui 742 pass (index gate rebuilt after commit). Independent review: 1 high (errored gate failed open), 6 medium (news partial outage, sweep crash loses rows, OOS reuse denominator, reset dropped events, resolution across gaps, full suite sweeping after a failed fetch); all fixed with regressions. Fee and funding-timestamp questions checked: no double fee (engine.py:200), funding time is the payment time. Sweep run 20261107T130441Z-f7fea5b2368e: 1,420 configurations over BTC/DOGE/ETH/SOL/ZEC 30d; none profitable OOS beyond luck; oracle (perfect one-bar call) nets -7 to -10 bps on four coins; reversion metrics >50% hit on all five, trend metrics <50% on nearly all.

Remaining: user runs research/full_suite.py for a year of 5m data; consider reversion-leaning defaults only after that out-of-sample year; prediction-markets component (prompt v17) not wired into the compound.

## v31 - 2026-11-07 (Hourly index sweep)

Target: "Set the idle indexer to do an index sweep once an hour even if not idle." Stele TASK-821. Reason: this Mac's load runs 8 to 12, so the load-under-2.0 rule never fired. index/idle.py: when the semantic index is stale and the machine is busy, a rebuild now starts anyway if an hour has passed since the last one started (state key last_build_at; INDEX_FORCE_INTERVAL seconds, 0 disables; never-rebuilt counts as due). A fresh index is never rebuilt; the lock and nice 19 still apply. `--install-schedule` writes ~/Library/LaunchAgents/com.mitchhudson.solmargintrader.index.plist (StartInterval 3600, runs `idle.py --once`, RunAtLoad false) and bootstraps it; `--uninstall-schedule` removes it. Tests: 9 added to test_index_search_tooling.py.

## v32 - 2026-11-07 (adaptive compound weights and tuning)

Target: user asked to multiply each compound metric by how often it is right, updated after every prediction; then to apply Bayes to each miss and move settings toward what would have been right; then to cap the counted record at two weeks ("we can dial it back"). Stele TASK-822. Worktree /Users/mitch/dev/solmargintrader-wt-e63b4616-adapt, branch feat/compound-adaptive-weights, PR #62. Previous work (PR #60, 41fa9e3) merged.

Completed: scorecard adaptive_counts (one-bar-lagged hit/call counts over a capped record: only the last adaptive_window bars count, default 4032 = two weeks; optional half-life fade inside it, default off), adaptive_multiplier (Beta-prior posterior, edge 2p-1, mute or flip), beta_posterior, p_better_than, neighbours and tune_component (shadow settings at x(1-step)/x(1+step), move only when P(better) > tune_confidence with tune_min_calls, re-centre, cooldown). adaptive defaults ON, tune OFF. soltui: live window up to 4,032 bars when adaptive, ledger_seed passes earlier resolved calls (k, hit, call) still inside the window with matching component_sig; call rows record sigs and multipliers; tab columns learned hit (n) and tuned to, Adopt tuned settings button (46 buttons). Docs COMPOUND-5M.md, skill v1.1.0.

Verification: backtester 817, soltui 745 pass. OOS hit rate of the default compound, static vs learned (two-week window): BTC 48.5/46.5, DOGE 44.0/55.6, ETH 45.6/52.0, SOL 46.3/50.2, ZEC 48.9/51.6; the window and the earlier one-week fade agree within 0.6 points. Tuning at 0.95 moved once in five coins; looser bars add a little inside noise. All returns still negative (16 bps round trip vs 6-9 bps moves). Live SOL: only reversion metrics earn weight.

Remaining: user may shorten or lengthen adaptive_window after watching it; per-regime learned weights not built; a year of 5m data via research/full_suite.py before trusting any of it.

## v33 - 2026-11-07 (Compound 5m paper)

Target: "Write a paper detailing the metrics, what they check, why they're included, what the tunable parameters are, and performance so far." Read as the compound five-minute scorecard. Stele TASK-823. Wrote docs/COMPOUND-5M-PAPER.md: scope, method, all 35 components (28 scores, 7 gates) with what each checks, why included, formula, works/fails and parameters, the four parameter layers, the evaluation protocol, and results recomputed from ~/.config/soltui/compound/backtests.jsonl run 20261107T130441Z-f7fea5b2368e (the file holds the same sweep twice). Headline: no configuration made money in a way that survives scrutiny (10 of 1,420 positive OOS, all within about 1.2 standard errors of a coin flip, 7 of 10 lost in-sample); default compound lost 17 to 63 percent OOS (mean -43 percent at 5x); oracle one-bar net is negative on all five coins; weak reversion pattern in rsi/zscore/bollinger/stochastic; no forward ledger exists and the year-long full suite has not completed. The paper's tables are generated from the catalog and saved rows by a scratch script (not committed); re-derive from the sweep file if the numbers must be refreshed.

## v34 - 2026-11-07 (compound: wallet, clicks, unattended training, inversion, new metrics)

Target: user asked (1) where wallet information should come from and to read it; (2) click a metric to toggle it; (3) a button for fully unattended forward training; (4) invert metrics that score badly; (5) a status bar for the backtest table; (6) add Volume, Balance of Power, ZigZag and EMA; (7) which signals are mutually exclusive. Stele TASK-824. Worktree /Users/mitch/dev/solmargintrader-wt-e63b4616-wallet, branch feat/compound-wallet-sizing.

Completed: wallet read from soltui Settings solana_address via wallet.scan_solana (public; SOL/USDC/USDT by mint; unpriced = unknown), size_call (min of usable x leverage and risk_pct to the stop incl. costs; engine liquidation formula), paper $ at wallet size in forward status, use_wallet/risk_pct execution settings. CompoundTable subclass: click on on/off or name cell toggles (Textual 8.2.8 only posts Selected on a second click), Space toggles. Unattended trainer: start/stop/status commands, detached `forward --loop --unattended` under taskpolicy -b, per-asset flock, stop file + SIGTERM, errors logged not fatal; tab buttons (48 total) and 60 s result refresh. adaptive_flip default 1. New metrics ema_trend, volume, bop, zigzag (non-repainting). Families regrouped by measured correlation: stretch (rsi, stochastic, cci, bollinger, zscore), ma-trend (+ichimoku), momentum (macd, roc). scorecard.relations + tab warning line. standalone_config now turns adaptive/tune off (bug: standalone rows were muted). run_summary status bar above the backtest table; CLI `results` prints it.

Verification: live wallet scan of the Settings address read $2.29 SOL and sized a call; live unattended start -> one recorded tick -> stop released the lock. Default compound OOS hit static vs learned+invert: BTC 50.3/49.5, DOGE 44.9/55.8, ETH 45.6/52.6, SOL 47.3/51.1, ZEC 48.3/51.1; returns still negative on all five.

Remaining: open Jupiter Perps positions are not read (no documented endpoint); per-regime learned weights; a year of 5m data via research/full_suite.py.

## v35 - 2026-11-07 (grid holdout)

Target: profitability review of the repo (prompts.md v28). Review verdict: strong safety/tests/docs, no measured edge, no realized profit, about $1 idle on the LP wallet; every tested strategy lost out of sample (PBO 0.70). Recommended: hurdle rule (beat jupSOL staking net of costs over 90 forward days), holdout rerun, forward shadow ledger, Trigger transaction verifier then one tiny live round trip, carry/yield backtest, regime-gated grid with a cancel path, monitoring (unified equity vs HODL, dead-man heartbeat, cache freshness, realized-vs-modelled costs).

Completed: PR #55 gitignored the two CDP credential files (merged c01412a; never read). Holdout: fetched SOL 1d to the scratchpad (not the shared cache), added research/grid_holdout.py and research/results/grid_holdout_20261107.json, section in research/GRID-REVIEW.md. Predeclared ladder on 94 finished bars 2026-08-05..2026-11-06: +0.83% (about 3% a year) vs hold +21.6%; price above the ladder 80 of 94 bars; double costs +0.81%. Worktree /Users/mitch/dev/solmargintrader-wt-97230e9e, branch agent-97230e9e.

Remaining: forward shadow ledger (dry-run against live prices, log modelled vs real fills); Trigger semantic verifier; carry/yield backtest; monitoring items above. grid_holdout.py has no unit test (thin glue over tested gridsim); add one with the counts update if it grows.


## v36 - 2026-11-07

Target: extend the existing triangular_arbitrage card, not add a duplicate strategy. Stele TASK-826; steps TASK-827 (feasibility), TASK-828 (design), TASK-829 (verify/deliver).

Worktree: /Users/mitch/dev/solmargintrader-wt-01a1b691; branch agent-01a1b691; base db3a3d9. Shared checkout has active sessions and unrelated untracked work; preserve it.

Completed: instructions, data/engine/card contracts, prior KNOW-522, and source abstracts inspected. The example multiplies to 0.99; reciprocal rates are hypothetical until reverse bid/ask is available. Existing card is spec-only.

Decisions: one venue, independent cross pairs, timestamped event replay; use bid for base sales and reciprocal ask for base purchases; include depth, latency, partial fills, dust and costs. KNOW-830 records this design; KNOW-831 records the data gap. Existing USD OHLCV cannot measure capture profitability. Scope is a card design, not a new runner.

Evidence: original abstracts at https://arxiv.org/abs/2105.02784 and https://arxiv.org/abs/0812.0913; crypto study at https://doi.org/10.1016/j.frl.2024.106508 and University of Bamberg repository. Read via Parallel on 2026-11-07 (cached source acquisitions disclosed by provider). Stele search agent failed because gpt-5.4-mini is unsupported on this account; direct MCP reads used.

Remaining: write card; verify arithmetic, card suite and docs/index freshness; regenerate offline retrieval artifacts as required; review/commit/push/PR/CI/merge; preserve other sessions. Missing historical books and a runner are future implementation requirements, not unfinished deliverables for this design request.


## v37 - 2026-11-07

Completed on /Users/mitch/dev/solmargintrader-wt-01a1b691: existing backtester/strategy_cards/triangular_arbitrage.md is design v2.0. It contains the corrected worked example, reciprocal-ask conversion, exact fee hurdle, independent-book requirements, delayed three-leg replay, partial-fill/unwind accounting, capital/depth reservations, holdout and stress protocol, acceptance gates, required future fixtures, and original source links. No runner, registry, or live execution changed. Prompt v29 preserves the verbatim request.

Verification: 40 strategy-card tests pass. Full backtester suite: 829 tests pass. scripts/check_docs.py passes (829 backtester, 313 extension, 33 mongo, 756 soltui discovered; only the backtester suite was run locally for this documentation change). research/verify_numbers.py passes its 1,084 existing research-figure checks; it does not validate literature figures in this card. Card arithmetic independently checked with decimal arithmetic. The first full-suite run failed only because index hashes were stale; offline index/build.py all repaired them and the next full run passed. No semantic indexing, model startup, data collection or live trading ran.

Delivery: commit and PR cover the card, these workflow records, and the three offline retrieval indexes. TASK-829 holds the final PR/check/merge receipt after remote delivery. The shared master checkout and unrelated branches/worktrees remain owned by their active sessions.

Remaining design work: none. Before any measured arbitrage result, a later implementation must audit venue/pair availability, obtain sequence-valid independent cross-pair books and fee/latency metadata, and implement/test the offline replay. The card deliberately remains spec-only with data_available false; profitability is unmeasured.

Integration: preserved the concurrent grid-holdout merge d991ec5 (PR #65), including its prompt v28 and memory v35. This task's records are now prompt v29 and memory v36/v37. Regenerated offline retrieval indexes after combining both histories; final checks run on the integrated tree.

## v38 - 2026-11-07 (every coin in parallel, own numbers, full minute history)

Target: user asked for data as detailed and as far back as possible, backtesting and forward testing on all coins at once in parallel, each coin with its own set of numbers. Stele TASK-825 (Stele MCP disconnected mid-session; writes queued in the outbox). Worktree /Users/mitch/dev/solmargintrader-wt-e63b4616-coins, branch feat/compound-all-coins (stacked on PR #64).

Completed: 1m history fetch started for BTC ETH SOL DOGE ZEC XRP BNB HYPE (`fetch_minutes --all --years 7`, main checkout data/). compound state gains per-coin overrides (state["assets"]) stacked on the base; save/reset take asset and scope (all, coin, everything); adopt tuned saves to the coin. materialize_bars caches 5m bars per coin (.npz keyed by source mtimes); workers hold at most two coins. backtest_all and the sweep use each coin's own config. Candle cache per coin (closed bars only) so a tick costs one request; 429/5xx retried. start/stop_unattended_all (staggered 6 s per coin, --offset). overview(); tab coin picker, scope switch, Backtest all coins, Start/Stop all coins, overview table (52 buttons). full_suite fetches 1m history instead of 365 days of 5m.

Remaining: run Backtest all coins once the minute download finishes and report per-coin results; open Jupiter Perps positions still unread.

## v39 - 2026-11-07 (compound data quality)

Target: before backtesting every coin on the full minute history, act on KNOW-523 (research/CANDLE-GAP-AUDIT.md): Coinbase drops minutes that traded, so the earlier claim that a missing minute means no trade (resample_complete docstring, KNOW-819) was wrong. Worktree /Users/mitch/dev/solmargintrader-wt-e63b4616-quality, branch feat/compound-data-quality. PR #66 (all coins) merged 2bb24f6.

Completed: resample_complete counts minutes per 5m bar; incomplete_pct per coin in prepare and every report; run_summary warns above 1%; overview shows it; bar cache format v2. KNOW-819 corrected and linked to KNOW-523; KNOW-531 updated for soltui's compound network/process exceptions.

Verification: minute history so far: BTC 2019-11.. 0.03% incomplete, ETH 0.50%, SOL 2021-06.. 1.04%, DOGE 4.49%, ZEC 60.3% (64% minute coverage). XRP, BNB, HYPE downloading.

Remaining: run Backtest all coins on the full history and report per-coin results.

## v40 - 2026-11-07 (top 50 coins, 1m history)

Target: 1-minute history for all 50 of the top 50 coins (pegged tokens left out), and the compound tester over every coin with data. PR #69 (data quality) merged 64cacbe. Worktree /Users/mitch/dev/solmargintrader-wt-e63b4616-quality, branch feat/top50-minute-history.

Completed: research/results/top50-nonpegged-2026-11-07.json (CoinGecko ranking; 36 on Coinbase USD, 14 not). backtester/core/fetch_minutes_alt.py fetches the 14 from OKX/KuCoin/Bitget/WhiteBIT against USDT, reorders KuCoin/WhiteBIT [t,o,c,h,l] rows, aborts on more than 1% impossible OHLC, writes a source.json sidecar the loader puts in the label. fetch_minutes takes --assets for any Coinbase USD product and merges the coverage manifest. soltui: coins() is every coin with data; non-Coinbase coins are backtest only; one unattended process ticks all live coins with per-coin locks and stop files. full_suite defaults to the top-50 record and sends only Coinbase coins to Coinbase steps.

Verification: test_fetch_minutes_alt, test_full_suite, test_compound pass; all four venues parsed live with 0 rejected rows. Downloads running in the background from the main checkout's data/.

Remaining: finish the downloads; deliver research/results/minute_coverage.json; run Backtest all coins on the full history and report per-coin results with data-quality caveats.

## v41 - 2026-11-07 (extension redesign, TASK-836)

Target: redesign `extension/` so holdings, P&L and alerts come first and the grid moves to its own last tab.
Worktree: /Users/mitch/dev/solmargintrader-wt-extui. Branch: feat/extension-redesign from origin/master 2bb24f6.
Decisions: swaps are quote-only with hand-off to the venue to sign (KNOW-837); pool alerts use measured scout APR, quoted DefiLlama APY is a labelled lead only (KNOW-838).
Data sources: Base JSON-RPC (mainnet.base.org, base-rpc.publicnode.com; chain 8453; `latest` tag since Denim), Solana JSON-RPC, DefiLlama coins + yields, Jupiter lite-api price and quote, soltui bridge for pnl.*, portfolio.*, liquidity.*, strategies/backtest/roster/top5.
Completed: tabbed dashboard (Overview first, Grid last) and new popup; registry commands holdings, pools, swapTokens, swapQuote, getPrefs, setPrefs, overview, scanAlerts, ackAlerts; src/market (read-only reads, Slipstream CL quote with range refusal, Jupiter Metis quote); src/core/alerts.js; alert alarm + notifications + badge; soltui liquidity.data; attribution names Metis (quotes) and Ultra (holdings); manifest 0.3.0 with notifications and read-only market hosts. Independent review fixed: scout gate (fresh, medium/high, unflagged, gauged, break-even), modelled label, scan/ack serialisation, lead baseline, hex validation, null APY, pool cache, manual-scan notifications, badge P&L, slippage refusal, stale quote panel, Solana mint validation.
Verification: npm test 351 pass; dry run net +$0.3492; npm run e2e 21/21; verify-endpoints pass; check_docs agree; soltui 767 run with 1 pre-existing Textual timing flake (#compound-unattended NoMatches in test_kill_and_resume_buttons_write_only_the_kill_file), module re-run 50/50.
Lessons: public Solana RPC 403s extension origins (KNOW for Jupiter holdings path).
Remaining: commit, PR, CI, merge.

## v42 - 2026-11-07 (editor bar, compound preview, toggle, autopilot)

Target: prompt v33. Autopilot keeps master's one-trainer design (#71): autopilot_ensure starts one process for every live-capable coin not running. Stele TASK-833; decisions KNOW-834 (autopilot) and KNOW-835 (double-click toggle). Worktree /Users/mitch/dev/solmargintrader-wt-splitpane, branch feat/soltui-split-preview-autotune.

Completed: `EditorBar` replaces the editor's orange border-top: drag to resize (clamped 3..screen-12), double-click resets to 16, "x close" hides the editor, a click / drag up / ctrl+e shows it, ctrl+up/down resize; height and open state persist in ~/.config/soltui/tui.json (only main() passes the path; test apps keep layout in memory). Selecting a compound metric, coin, backtest row or forward call shows a read-only markdown preview in the shared editor (`compound.metric_preview`, `coin_preview`, `record_preview`); a preview never replaces unsaved edits and never fires from a background refresh while another tab is active. CompoundTable toggles on double-click (Click.chain == 2) or Space; a single click only selects. Autopilot: top-level `autopilot` flag in compound config.json (missing = on); on overlays aggregate.tune=1; forward_tick adopts tuned_params as the coin's own settings via `auto_adopt` with a per-metric tune_cooldown read from `adopt` ledger rows; save_state holds an flock (config.json.lock). `autopilot_ensure` starts any coin's unattended loop not running; registry `compound.autopilot` (set), `compound.autopilot_status`, `compound.autopilot_ensure`; CLI `python -m soltui.compound autopilot`; LaunchAgent `com.mitchhudson.soltui.compound-autopilot` via `python -m soltui.compound_agent install` (refuses a worktree). The console's main() also runs ensure once at start. 53 buttons.

Honesty: tuning at the 0.95 bar rarely moves (docs/COMPOUND-5M.md: one move in five coins over 30 days) and backtested returns stayed negative; autopilot automates the evidence-gated search, it does not make the compound profitable. Paper calls only; no order path.

Remaining: none in code; install the LaunchAgent from the main checkout after merge.

## v43 - 2026-11-07 (ten-coin compound universe)

Target: the owner asked which top-50 coins fail before testing, then chose BTC, ETH, SOL, XRP, HYPE, DOGE, LINK, NEAR, SUI, AVAX. Stele TASK-844. Worktree /Users/mitch/dev/solmargintrader-wt-e63b4616-quality, branch feat/compound-ten-coin-universe.

Completed: research/results/top50-screen-2026-11-07.json (live CoinGecko turnover, Hyperliquid perp leverage, Coinbase status; verdict and reason per coin; 13 disqualified, 8 caution). COMPOUND_5M_UNIVERSE in backtester/core/universe.py; soltui compound COINS and coins() use it, so cached data for other coins no longer joins Backtest all or unattended training; full_suite defaults to it. Docs and the five-minute-signal skill (1.5.0) say so. The 36-coin and 14-coin downloads were stopped (SIGINT, kill-safe) and a 10-coin Coinbase fetch restarted.

Verification: test_universe (screen matches code), test_full_suite, test_compound pass.

Remaining: finish the 10-coin download (NEAR, SUI, AVAX are new); deliver minute_coverage.json; Backtest all coins on the full history; report per-coin results.

## v44 - 2026-11-07 (Backtest tab, wallet, key files, table titles)

Target: prompts v35, v36, v37. PR #68 (editor bar, previews, toggle, autopilot) merged as 288502d. Branch feat/backtest-tab-titles-wallet from that master.

Backtest tab: a "Strategy to backtest" Select (whole roster or one roster label) and a line listing the roster; `backtest.run` takes optional `labels` and refuses labels outside the roster. The old "Run Untested Sweep" ran research/sweep_untested.py, which printed the untested names and then backtested a fixed handful on one horizon. The button is now "Backtest untested + little-tested": `queue.backtest` scope `undertested` (never tested, or fewer than `min_runs`=3 recorded configurations) with `max_tier=1`, started at once in the background worker; progress shows in `#backtest-bg-status`.

Wallet: soltui settings already kept the addresses (~/.config/soltui/config.yaml). The scan lived only in the Wallet tab's widgets. `portfolio.scan` now keeps its result in `~/Library/Application Support/soltui/portfolio/last-scan.json` (mode 600); `portfolio.last` returns it; the real console (main() passes refresh_wallet=True) shows it at start and re-scans in the background. Test apps never read it.

Key files: verified by running the loaders, never printing key material: `aero_lp.wallet.load_signer` with ~/.ssh/wallet.private controls 0x901a89cEC0608eB5435A915f006b45bD46405314; ~/.ssh/solana.private is a 64-byte keypair for EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV; both mode 600. CLAUDE.md rule 4 and liquidity/CLAUDE.md now say agents run the programs that load the keys to sign and move money (KNOW-840). Not changed: the extension's FULL_AUTO passphrase stays unpersisted, and extension live signing stays blocked without a semantic transaction verifier.

Table titles: every DataTable has a `.table-title` Static above it (bold, accent colour); the compound titles name the selected coin. `TableTitleTests` fails if a table lacks one.

Remaining: install the autopilot LaunchAgent from the main checkout; restart the running console so it loads the new code.

## v45 - 2026-11-07 (Hyperliquid costs)

Target: the owner confirmed Hyperliquid access, so all ten coins are live candidates and their backtests should pay Hyperliquid's costs. Branch feat/compound-hyperliquid-costs. Stele TASK-844.

Completed: research/results/hyperliquid-costs-2026-11-07.json (live userFees base schedule: taker 0.045%, maker 0.015%; one l2Book walk per coin at $2k/$10k/$50k). scorecard EXECUTION_SPECS fee_bps default 6.0 -> 4.5, so the default round trip is 13 bps (16 on Jupiter). Docs and the five-minute-signal skill (1.6.0) updated. The owner's saved shared config still holds fee_bps 6.0; set it to 4.5 after merge with soltui.compound.save_state.

Also: Hyperliquid maintenance margin per coin (HYPERLIQUID_MAX_LEVERAGE in backtester/core/compound.py; 1/(2 x max leverage)) now drives engine liquidation, the sized call's liquidation price and gate_liquidation. Jupiter's 0.2% stays for other coins. The owner's saved shared config fee_bps was set to 4.5 (backup in the session scratchpad).

Verification: test_compound_backtest expects 13 bps; new tests cover the margin table against the screen, earlier liquidation, the gate and the sized liquidation price.

Remaining: wallet sizing still reads the Solana wallet (Jupiter collateral); a Hyperliquid account balance read needs the owner's Hyperliquid address. Then the ten-coin full-history backtest (TASK-844).

## v46 - 2026-11-07 (Hyperliquid account sizing, ten-coin backtest)

Target: the owner confirmed their Hyperliquid account is 0x901a89cEC0608eB5435A915f006b45bD46405314 (the Base address). Branch feat/compound-hyperliquid-wallet (on top of feat/compound-hyperliquid-costs, PR #75).

Completed: Settings field hyperliquid_address (default the owner's address; EVM-validated; refuses private material; Settings tab, help, wallet.addresses). soltui.compound.hyperliquid_balances reads clearinghouseState and spotClearinghouseState read-only: usable = perp withdrawable, spot USDC shown not counted, positions listed, a failed read is unavailable. signal, forward_tick, unattended and the commands size from it when set; the Solana wallet is the fallback. Live read on 2026-11-07: account value $0, no positions, no spot balances.

Verification: new tests for an empty account, funded account, failed/malformed read, and preference over the Solana wallet.

Ten-coin full-history backtest done: run 20261107T192614Z, 300 configurations, Hyperliquid costs and margins. All 300 lost the stake out of sample at 5x. Reversion metrics beat a coin flip on every coin (RSI z 13-23) but earned at most 0.6 bps per call against 13 bps. A perfect one-bar call nets positive on 8 of 10 coins at 13 bps. NEAR/AVAX/HYPE/SUI/LINK have 11-38% incomplete bars. Results: research/results/compound-10coin-fullhistory-2026-11-07.json; docs/COMPOUND-5M.md findings section. Coverage: research/results/minute_coverage.json.

Remaining: the owner must deposit USDC to Hyperliquid before any call can be sized. Untested ideas: multi-bar holds, maker entries, fewer stronger calls.

## v47 - 2026-11-07 (SOL one-sided calls)

Target: the owner saw only UP calls and composites of at least 0.5 in the SOL forward test. Stele TASK-850. Worktree /Users/mitch/dev/solmargintrader-wt-e63b4616-vwap, branch fix/compound-vwap-saturation.

Found: the composite arithmetic is right (recomputed 0.5009 = logged). vwap_reversion scaled the session-VWAP distance by one 5m ATR and sat at +1.00 on every SOL bar 17:25-20:05 UTC (57% of the last 60 days). Its family weight added about +0.35. Only reversion metrics had learned weight. Three stale unattended processes plus the TUI wrote some bars twice (no lock between the ledger read and the append).

Completed: _vwap_distance divides by the RMS of the distance over spread_window (288) bars, floored at ATR, which leaves about 8% saturated. FORMULA_VERSIONS goes into component_sig, so the two VWAP metrics' learned records restart while other metrics keep their signatures. _append(unique=True) re-checks ids under a per-coin flock. ledger_seed counts one call per bar.

Verification: replaying live SOL bars, vwap_rev saturation fell from 92% to about 0% over the last 4h; the last-4h calls went from 26 UP / 0 DOWN to 22 UP / 1 DOWN with more FLAT; all bars are balanced (616 UP / 544 DOWN).

Remaining: after merge, restart the unattended trainers for the ten coins only (the stale ones still train ZEC, BNB, ADA and XLM on old code). The owner must restart the soltui console to load the fix.

## v48 - 2026-11-07 (TradingView docs distillation)

Target: the owner dropped `tradingview/` (TradingView Advanced Charts docs bundle, three `.d.ts` files, agentskills.io llms-full) and asked for every indicator, signal, script and equation distilled into one Markdown file. Stele TASK-853 (dev-y3seh, COMP-320); decision KNOW-854. Worktree /Users/mitch/dev/solmargintrader-wt-tradingview, branch docs/tradingview-reference.

Completed: `docs/TRADINGVIEW-REFERENCE.md` (13 sections): indicator parity table (repo `indicators.py` vs TradingView built-in defaults), licensing limits, 114 built-in studies with inputs/defaults from `StudyOverrides`, 114 `PineJS.Std` entries and custom-indicator metainfo, datafeed/UDF/marks contracts with a zero-dependency datafeed sketch, chart/drawings API with on-chart recipes, 193 featuresets and widget options, Broker API concepts mapped to the extension's rails, release notes to v33.0.0, Agent Skills spec, repo findings. Seven parallel readers produced fragments; spot checks of `getBars`, `OrderStatus`, `Std.atr`/`Std.stdev` matched the `.d.ts`.

Constraints found: Advanced Charts is free only for public, attributed deployments ("not for private use"); any part of the library is prohibited in public repos. The repo is public, so `tradingview/` is gitignored and nothing from the library is committed. Lightweight Charts is the only TradingView product that fits a private tool, and it conflicts with the extension's zero-dependency rule.

Verification: `scripts/check_docs.py` (venv) passes; `index/build.py --check` passes after `build.py all`, `make_files_doc.py`, `make_concepts_doc.py`.

Remaining: repo findings listed at the end of the reference (z-score ddof mismatch between card and Compound 5m; skills frontmatter violations; no ledger-to-chart exporter) are recorded, not fixed.

## v49 - 2026-11-07 (research landed; frontier; fees; Base wallet via CDP)

Target: prompts v42 and v43. Branch research/land-and-frontier, PR #78 (https://github.com/mithudso/solmargintrader/pull/78).

Landed: the untracked research in the main checkout (research/*.json, *.md, docs/profitable-crypto-strategies-analysis.md, curated llms/ notes). Gitignored: auth/ (CDP API key and wallet secret, never committed), .codex/, llms/ doc mirrors. Other worktrees were all pushed; fix/compound-vwap-saturation belonged to a live session (merged as #77); PR #58 (draft research checkpoint) and #46 (executor, money-moving) were left for their owners.

Built: scorecard `hold` and `entry_quantile` (both off by default), forecast `horizons` (net bps by holding period), six research metrics off by default (keltner, mom_skip, vr_regime, ou_reversion, consec_run, pairs_spread); compound frontier variants (every metric alone, top 2%, held 1/4/24 h, 1x), buy-and-hold per window, re-lever on 10% drift (trade counts had counted every bar's drift); Compound tab in four sections with a What-is-tested paragraph, readable row names, buy & hold and net bps 1h/24h, Frontier button; research/frontier_tune.py (in-sample-only tuning plus related search).

Findings (research/COMPOUND-FRONTIER.md): reversion metrics' 52% hit is about 0 bps gross at every hold; only htf_trend survived the frontier (top 2%, 1-4 h, 1x: OOS positive 8/10, beat B&H 7/10, in-sample Sharpe about 0, OOS mostly falling); in-sample tuning made things worse out-of-sample; mom_skip at top 0.5% held 48 h, 1x: OOS +0.75 median Sharpe, positive 8/10, beat B&H 6/10, chosen after 1,227 configurations per coin — a forward-paper-test candidate, not a funded strategy. Leverage: SOL htf_trend same calls +20% at 1x, -53% at 5x.

Base wallet: docs/BASE-WALLET-QUERIES.md (CDP MCP recipe); gtUSDCp (Gauntlet USDC Prime, about $86.64) added to KNOWN_BASE_TOKENS; KNOW-852; auto-memory base-wallet-cdp-queries.md.

Remaining: forward paper test of mom_skip top 0.5% 48 h (not built); maker-fill modelling (no fill-rate data).

## v50 - 2026-11-07 (Lightweight Charts; /dso v2)

Target: owner chose Lightweight Charts (KNOW-859, TASK-860, dev-y3seh) and asked for every evaluation method plus a one-pass-per-method /dso. Worktree /Users/mitch/dev/solmargintrader-wt-lwc, branch feat/lightweight-charts.

Completed (this repo): vendored lightweight-charts 5.2.1 standalone ESM in extension/vendor/lightweight-charts/ (LICENSE, NOTICE, README with npm integrity and file sha256); src/ui/charts.js lazily imports it, draws the grid view's equity curve with the attribution logo on, and falls back to the SVG; test/charts.test.js pins the sha256 and tests the data mapping; CLAUDE.md House style and docs name it as the one runtime library.

Completed (skills repo, not this repo): deep-strategy-optimizer 2.0.0, PR mithudso/skills#90 (45903ec52): 400 evaluation methods, 273 passes in 9 families, legacy mapping, evals, /dso command. docs/dso-skill here is now a stale v1.1.1 copy (Stele KNOW-344, skills project).

Remaining: none for the chart; docs/dso-skill could be replaced by a pointer in a later change.

## v51 - 2026-11-08 (resume Compound 5m)

Target (Stele TASK-862): run a fresh combined registry and compound sweep across the owner-selected ten coins. The tester and skill shipped in PR #60 and subsequent improvements through PR #78. The recorded ten-coin full-history result covers 300 compound configurations, not the full registry plus compound sweep.

Checkpoint: started the data refresh from the isolated agent-01a1b61a worktree; the fetch log is in the main checkout at data/logs/full-suite-resume-fetch.log. The full suite now includes frontier variants and passes the absolute refresh cache to registry workers. The new --archive-results flag allows --skip-fetch to start a new registry ledger after a successful standalone refresh. A detached continuation waits for a successful fetch before running both sweeps; see data/logs/full-suite-resume-sweeps.log.

Verified: 60 focused tests and check_docs pass. Remaining: verify per-asset fetch coverage, completed registry and compound rows, skips and errors before interpreting the new run. Keep the worktree while the continuation uses it.

## v52 - 2026-11-08 (trend filter)

Target: the owner asked for a filter that stops the compound fading a clear trend. Worktree /Users/mitch/dev/solmargintrader-wt-e63b4616-trend, branch feat/compound-trend-gate.

Completed: Component.directional; gate_trend (htf_trend formula; threshold 0.5; default on). A directional gate returns a direction per bar, and evaluate blocks only a call against it (NaN blocks all, failing closed), so blocked_by and target_path work unchanged. Docs and the five-minute-signal skill updated.

Verification: tests cover blocking UP in a decline, keeping DOWN, explain blocked_by, warm-up failing closed, and prefix invariance. Last 120 days OOS: threshold 0.3 keeps 35-45% of calls and lowers the hit rate on 7 of 10 coins; 0.5 is about equal on SOL/ETH/XRP and about 1 point lower on BTC/DOGE; 0.7 is equal or higher on SOL/ETH/XRP. Live SOL, last 6h: 26 UP / 8 DOWN became 0 UP / 8 DOWN.

Remaining: after merge, restart the unattended trainer so it runs gate_trend; the owner restarts soltui.

## v53 - 2026-11-08 (Adaptive Forwardtest)

Target: prompts v46, Stele TASK-863 and KNOW-864. Worktree /Users/mitch/dev/solmargintrader-wt-forwardtest. Reuse compound tuning gates on prospective shadow predictions. Isolate each trial and each of four horizons. Implemented Space toggle and bulk roster add. Added a console-owned paper Forwardtest worker, closed 1m Coinbase feed, SQLite prediction history, separate 1/5/10/30-minute trials and shadow learning gated by paired resolved observations. Nine focused tests passed for separate outcomes, pre-window timing, missing data, adoption, roster and worker stop. The 853 backtester tests and documentation checks passed. An isolated SOL tick recorded all 140 calls for 34 standalone strategies and one combination across four horizons. Full local suite caught missing shared glossary entries and the Forwardtest table title; corrected both. Remaining: confirm full CI and merge PR 83 (https://github.com/mithudso/solmargintrader/pull/83).

## v54 - 2026-11-07 (Five-minute leveraged perps full-suite)

Target: research five-minute SOL Jupiter Perps directional signals and adverse-path survival. Task TASK-808. Private worktree /Users/mitch/dev/solmargintrader-wt-01a1b5ef, branch agent-01a1b5ef at c01412a. Preserve all shared checkout and other worktree changes.

Completed: read project instructions and routing index; full-suite is folded under llms-txt-tooling/references/full-suite.md. Fetched KNOW-656 (dated cost mechanics) and KNOW-657 (data/execution gap); created decision KNOW-809 separating terminal direction, barrier survival and net expectancy. The stele-search agent failed because its fixed gpt-5.4-mini model is unsupported; direct named-node reads are the fallback.

Constraints: research only, no trading or execution/config changes. No keys, signing, daemon restart, inference or indexing services. Full-suite saturation and gate receipts must be earned, never inferred from artifacts.

Remaining: map coverage and scored gaps; research current venue and short-horizon predictive evidence; compile source packs and rollup; independent audit; offline indexes/docs checks; commit/PR/CI/merge and remote verification.

## v55 - 2026-11-07 (Full-suite preparation and audited private draft)

Completed: full canonical-tree inventory, 30 scored candidates across five neighborhoods, 23 HAVE and seven distinct above-threshold gaps. Canonical CVS checker passed all 30 rows. Verified 47 prior canonical SUPPORTED claims against 114 bound snapshot spans with zero missing/hash/offset failures. Seven preliminary scouts preserve leads, not evidence. TASK-810 complete; research TASK-811 and parent TASK-808 remain unfinished.

Current sources: refreshed four official Jupiter JLP pages and one exact-five-minute Binance empirical paper into private source library. KNOW-813 records current minimum linear-impact fee, jump-rate borrow curve, rolling flow imbalance and dual execution paths; KNOW-656 now carries a current-source caveat and contradicts edge. Do not treat the August fee-only model as current execution pricing.

Private draft: /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-task808-unpromoted/FIVE-MINUTE-PERPS.md (SHA256 ceef7f86d2aa505eff5a484f66eb7a2caae3f8650fad0374e19cf2245bf977b3) and calculated-scenarios.json (SHA256 c8fae31cce7f1edc7eaefdde6bbbfb6a609515f07597d7c785636109a720ecd4). Independent research-contract-auditor found no material source/math/scope errors; verified five snapshot hashes, 15 leverage scenario values, five symmetric probabilities and one asymmetric probability. This is a scoped synthesis, not a completed full-suite or v4 publication receipt. No profitable five-minute SOL strategy is claimed.

Blocker: python3 /Users/mitch/.global-ai-hub/scripts/dr_run.py check exits 1: retired research sink still present: /Users/mitch/.research. Installed /Users/mitch/.claude/commands/dr.md says to stop and report this condition. Directory contains about 23 MB of unrelated older local-model research. User async approval is pending for intact archive to /Users/mitch/.global-ai-hub/research/.legacy-archives/research-20261107-task808. Preserve it until answered. No new /dr init/research/gate/render/finish/tree write or service startup.

Verification: system Python lacked pandas; existing /Users/mitch/.venvs/soltui/bin/python ran research/verify_numbers.py successfully (1084 archived figures; not a new performance test). scripts/check_docs.py passed with counts 734/313/33/682. No product code changed; new scenario invariants and independent recomputation passed. Private reuse-only pack: /Users/mitch/.global-ai-hub/llms-concepts/five-minute-perps-inherited-v4.llms/. It retains 47 exact inherited supported assertions and 47 FTS5 rows. It is a private draft, not a new researched family: semantic/agent tests are absent, and facts-format lint conflicts with exact-proof reuse. The run-state receipt records all limitations. Remaining: on approved archive, run adapter research/gates on seven gaps, quality audits, final packs/rollup/index/tree steps and saturation gates. Preserve inventory and successful source reads. Repository recovery delivery is tracked in TASK-808; verify its PR status rather than assuming merge.

## v56 - 2026-11-07 (Private reuse pack and recovery checkpoint)

Completed: private source-bound reuse pack retains all 47 unchanged supported assertions. Keyword FTS5 has 47 rows and four nonzero query checks. Vocabulary and digest repairs pass their relevant checks; exact long assertion formatting still conflicts with facts lint and remains an explicit qualification limit. Semantic indexing and agent tests were not run. No source-derived new research draft is staged for the public repository.

Current recovery task: integrate origin/master 3cc9b44 without losing the other session's continuation records, refresh three offline indexes, commit and push the task branch and open a draft PR. Parent TASK-808 remains unfinished. User archive decision remains pending. Do not run new /dr work or alter /Users/mitch/.research before the answer. Delivery receipt belongs in TASK-808; all research stages after preparation remain owed.

## v57 - 2026-11-07 (Draft recovery delivery)

Recovery PR: https://github.com/mithudso/solmargintrader/pull/58 (draft; unfinished research checkpoint). Branch agent-01a1b5ef, private worktree /Users/mitch/dev/solmargintrader-wt-01a1b5ef. The branch includes origin/master 3cc9b44. Rebase conflicts in prompts.md and memory.md were resolved by retaining the upstream session's records and appending this task with unique version numbers. The shared dirty checkout was preserved.

Checks after integration: documentation drift passed with 734 backtester, 313 extension, 33 mongo and 712 soltui tests discovered. Offline source index check and whitespace checks passed. Independent private synthesis/math audit passed its stated scope. Canonical CVS checker passed all 30 rows. No product code changed. CI must be checked on the final pushed tip; its status is recorded in TASK-808 rather than presumed from a push.

Private reuse compilation: vocabulary check passes, digest fits 1603 estimated tokens and 6443 bytes, and FTS5 has 47 rows with four successful queries. Two facts-format Medium findings remain (facts/full ratio and 44 long assertions). The exact inherited assertions were preserved; no CLEAN label or new full-suite completion is claimed. Semantic indexing, agent tests, new per-concept research, rollup, skill audits/install/sync, tree registration and saturation gates remain owed.

Current blocker: archive decision for /Users/mitch/.research is still pending. Preserve its approximately 23 MB of older local-model work and do not run dependent /dr stages before the owner answers. The independently audited unpromoted report, calculations and audit receipt remain private under /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-task808-unpromoted/. Canonical CFE checkpoint and the public run-state copy preserve the seven queued gaps. No session-owned agents, services or inference jobs remain running. Parent TASK-808 and research child TASK-811 stay unfinished.
## v58 - 2026-11-08 (Approved archival and full-suite continuation)

Target: user approved intact archival and continuation of TASK-808. Refreshed instructions, current master, PR58 and accepted checkpoints. Reclaimed own stale TASK-808/TASK-811 records. Original source and requested target are absent. TASK-832 records the earlier user archive /Users/mitch/.research-archived-2026-11-07, which exists. Record complete before/after relative-path, type, permission and file-content inventories while relocating that preserved archive to the approved exact destination. No pre-November-7 manifest exists, so only this move can be verified.

Current /dr preflight passes. All seven queued gaps retain missing five-minute/executable/survival/calibration deltas. New Jupiter and microstructure packs provide source leads but their heuristic/legacy sampled receipts do not establish v4 verification. Preserve 47 previously supported assertions and successful reads. Root owns workflow records, archive, synthesis and Git delivery; coordinator owns actual seven-gap research, gates and compilation. Worktree /Users/mitch/dev/solmargintrader-wt-01a1b5ef; branch agent-01a1b5ef.

Remaining: archive verification; reconcile resolved blocker; actual adapter research/gates, quality audits, private packs and rollup, authorized index/tree placement, independent review and final repository delivery. No trading, signing, wallet changes or service startup belongs to this task.

## v59 - 2026-11-08 (Approved archive verified)

Completed: relocated the user-preserved archive /Users/mitch/.research-archived-2026-11-07 to /Users/mitch/.global-ai-hub/research/.legacy-archives/research-20261107-task808. Exact before/after inventories match for 1802 files, 34 directories, no symlinks and 18822683 bytes. Hash 4e70f32dc2cd59f308c74c485fb76ca2e1fc1d49239ab6105fdedac36a165d2d binds paths, file types, modes, owners, modification times and file SHA256 hashes. Private full manifest is adjacent to the archive; public summary in research/five-minute-perps-suite/archive-receipt.json. This verifies this relocation only, not the earlier user move for which no per-file baseline exists.

/dr preflight passes; KNOW-814 archived as resolved and KNOW-861 updated. TASK-808/TASK-811 are claimed by the current continuation. Merged current master 1f90856 into task branch as 5cf5918, preserving all upstream source and continuation records. Upstream has preexisting duplicate memory version28 and Markdown hard-break whitespace; preserved both rather than rewriting unrelated history. Task-only whitespace checks should use origin/master...HEAD.

Coordinator authorized to execute the actual standard-depth seven-gap adapter cohort with max parallel3, native scout/library support and default model/effort. Retain old47SUPPORTED proofs and successful source reads. Broad new packs have heuristic or legacy sampled proof; do not mark gaps HAVE from them. Independent code inquiry checks whether the repository's negative average all-bars perfect-direction ceiling was overgeneralized to selective five-minute signals. No backtest sweeps, wallet operations or live-service changes are authorized by this research-only task.

Remaining: actual research/gates and per-concept artifacts, quality/rollup/index/tree stages, evidence-based frontier and final audit; scoped docs/index checks, final PR58 update/CI/merge and remote verification. Root owns prompt/memory, archive receipt, synthesis and delivery; coordinator owns research metadata and task-specific private research outputs.


## v60 - 2026-11-08 (Full-coverage gate and benchmark scope)

Completed: independent archive audit rehashed every recorded file and metadata field with zero mismatches. Added research/five-minute-perps-suite/benchmark-scope-review.json and corrected docs/COMPOUND-5M.md plus docs/COMPOUND-5M-PAPER.md. forecast_stats.oracle_net_bps uses all time-selected close-to-close log returns, including ties and no-call periods; it does not condition on calls or model next-open execution and liquidation paths. A synthetic actual-function check gives the same negative all-bars diagnostic with a positive selected-call result. This is a logical counterexample, not market performance. Leverage multiplies proportional price returns and fees together; it does not lower their underlying break-even. KNOW-818 now records this correction. Historical numbers remain unchanged.

Research: all seven commissioned native returns completed, with 110 structured claims and 55 auxiliary assertions. Ten initial integrity pairs received one bounded repair. Actual research-gate/v4 packet 23848f133a76fd55d8eaac94a05fcd2dda5149c15cdd3a22baa0d5491a3555df selects all 165 assertions and has zero structural failures; independent semantic review is running. Draft completion is not evidence acceptance. Preserve source origins, successful exact reads and prior47SUPPORTED claims.

Delivery isolation: skills branch research/perps-task808 in /Users/mitch/dev/worktrees/skills-perps-task808; website branch research/perps-task808 in /Users/mitch/dev/worktrees/llms-explorer-perps-task808. Prompts and continuation records were saved before downstream writes. Supported render --out targets the private skills tree. Deliver and activate the qualified reference first, then rerender to its stable recognized path before canonical finish; otherwise the tree skill ID can be null and the manifest can point to a deleted worktree. Preserve unrelated dirty canonical skills and website checkout contents. Scoped parity registration includes only the new reference, hub routing, companion version/date and portable indexes, with baseline validation findings disclosed.

Semantic scope: later November7 explicit user authorization supersedes the historical blanket pause for this task's on-demand local indexing only. Use existing local Ollama mxbai-embed-large:latest; no model download, service start, LAN/eGPU window or background queue resume. Actual full-suite stages, final independent publication audit and all Git deliveries remain owed. Unit verification is running on this private integrated branch; archived numerical verification passed1084 checks and documentation drift passed.


## v61 - 2026-11-08 (Accepted v4 research and install qualification)

Accepted: final research-gate/v4 packet53f1e45fae9cc0570ca7ba4085ad120785c3928beef135a4809ed0261191023c reviewed165/165 assertions. It has125SUPPORTED factual assertions and40non-assertions; three conflicts have explicit attribution. The validator reused159 exact judgments and reviewed only6 changed rows. Public metadata-only receipt: research/five-minute-perps-suite/accepted-gate-receipt.json. Private final attempt: gate/attempts/20261108T071503.072906Z-fe9b6245 under the task's canonical run directory. Failed attempts and successful evidence remain preserved; no sampled or invalid response was promoted.

Root authored research/FIVE-MINUTE-PERPS.md from accepted venue mechanisms and prior supported microstructure evidence. Signal priority is explicitly a proposed test order, not an empirical winner. The 14bp round-trip floor and collateral percentages are labeled calculations from documented fee components; the binary80% example is arithmetic, not observed accuracy. No new market backtest, trading change or live trade. Independent final synthesis review is underway.

Skill installation: reference rendered in the isolated skills worktree. A banner before YAML caused meta-validation High 'no parseable --- frontmatter block' and empty index metadata. Coordinator normalized formatting only, preserving claim prose and evidence; KNOW-869 records the trigger and required stable-rerender normalization. Owning-hub offline audit found an existing hard body ceiling violation; the exact long routing descriptions were moved losslessly to trading-and-investing/routing-detail-catalogue.md. Every68table row/67unique route remains, including the preexisting duplicate. Hot card audit now0High0Medium; parity agent regenerates and validates final routing/index metadata. Preserve .agents model/omissions and its own version lineage during additive activation; do not replace the whole loaded hub. KNOW-867 records the stable-path hold.

Verification: extension361 passed; real browser dry-run22/22 passed; offline roundtrip net+0.3492; mongo33 ran,17skipped without local server. Backtester853 ran with only the expected stale-index guard failing while metadata is changing; rebuild after final freeze and recheck. SolTUI808 still running. Docs drift passed853/361/33/808,2055total. Site dependency Python manifests match existing venv; private symlink reuses it. Installed private site lock with scripts disabled because original site's dependency versions differ. Site typecheck has0errors/0warnings,19hints. Prebuild site tests273pass20skip and35missing-dist failures require actual build after finish; this is not a code failure or final acceptance.

Remaining: final qualified skills delivery and guarded activation, supported stable rerender, canonical finish/private/public boundary audit, actual per-concept/rollup compile/index/registration/frontier gates, final site build/tests, root/site PRs and CI/merge/content verification. ParentTASK808 remains unfinished.

## v62 - 2026-11-08 (Integrated delivery and qualified research skill)

Merged origin/master55c1dd4 (other-session gate_trend PR82). Preserved upstream prompt45/memory51, then appended this task's records as prompt46-47 and memory52-59 without changing request text or accepted source facts. Preexisting duplicate memory28 remains upstream-owned. Original forecast_stats AST is identical at current upstream and reviewed5cf5918 (SHAe00005b65a01e0bf9c70e85893c0b31e74afe65fe5eca1ecee024f0f0d6598ca); currentline1935, oldline1904. This task changes no strategy or execution code.

Root synthesis research/FIVE-MINUTE-PERPS.md passed independent factual/math/proposal review atSHA23cb83fbecd903c5b9f1fbc6a5fa07e73726def4a76cdd1c650ce7b854d90431; receipt in research/five-minute-perps-suite/synthesis-audit-receipt.json. SolTUI808tests passed with2skips before upstreamintegration. Remaining indexstaleness is expected until final research metadata freezes.

Skills delivery complete: https://github.com/mithudso/skills/pull/91 merged5765c8d755322292b6076d116a7b8e3a4526567b after finaltipf986579772de0d41f761cd1df4b208a3113d1b33 and passingoffline-safetyCI. Exact scopedcontent matchesorigin/main. Finalparent7116bytes plus7nestedguides preserves110exactclaims/7overviews/158bullets/68citationdefinitions; independentauditor accepted both length/privacy repairs. Guarded writer activates with freshhashes/backups, preserving dirty originals and distinct .agentsrouting/model. Canonicalportableindexes differ from deliverybase and need scoped repair, neverwholecorpusreplacement. Stablemanifest path repair must repeat deterministic partition after supportedrender.

Current privateLCA work has7single-filev3packs from110uniqueacceptedunits with15earnedterms perconcept; localvector/FTS indexes initially110rows eachaggregate. The fixed usability bank found missing contextualcost/validation answers in onepack; coordinator repairs only relevantacceptedcohortcontext and keeps original questions. Do not call usabilitypassed or full-suitesaturated until actualreceipts. Canonicalfinish/sitepublication remain held untilactivation/discovery/privacy preconditionspass. RootPR58 staysdraft until finalresearch/pack/quality/frontier/site/deliverywork completes.


## v63 - 2026-11-08 (Full-suite qualified; final delivery)

Completed conceptualCFE SATURATED after2of3defaultemptyexpansionrounds andfreshblindaudit;57scoredrecords,7researchedconcepts, no newabove-thresholdgap. Actualv4cohort165/165reviewed,125SUPPORTED/40non-assertions,110uniquestructuredclaims. Source65/70affirmativequestionanswers and70/70correctresponses (5genuineabsence disclosures), coverage35full/30partial/5absent; these do not establishcompleteknowledgeorprofit. Privatecurrentv3packs retain110uniqueclaims/164derivedrows with164vectors+164FTSrows and7memberrollup. Categoricalnavigation5/5, sourcebound118excerpts, fixedsemanticretrieval≥8/10all7. Exactlimitsandprivateproofhashesareinfull-suite-receipt.json andrun-report.md.

CanonicalfinishCOMPLETED/n warnings; artifactSHA1254521eda688b644884b05e9bb69be9922b7de9759a38c1cc82b0ea9e48c349. Sourceauditverified365spans/63snapshots,8publicprojections/16private-publicpacks,8readerpages and344internal links;328site tests and2849pagebuildpass. Combinedoperatorprivacyscan18611files/0findings. Baseline3historicalnotematchesredacted; unrelatedgeneratedallowlistexceptionsremoved. FinalCFEscore/placement applykept2866/2709nodes andbaseline308/312structuralissues, no newissues/queue; partiallegacyhookfailurewasrecoveredwithdocumentedprocess-localdisableandprojectvenv, explicitboundedregeneration. Rootroutinginstallerpreservesexistingbroaderfamilypointer.

Skills PR91merged5765c8d755322292b6076d116a7b8e3a4526567b andactualdiscoveryaccepted. WebsitePR https://github.com/mithudso/llms-explorer/pull/305 atd8f6fab2 containsqualifiedcohort;CIpending. RootPR58willcarryfinalmetadata,synthesis,benchmarkscopecorrection,instructionroutingandofflineindexes. Alltasksourcechangesshipthroughprivatebranches; sharedoriginaldirtyworkpreserved. Remaining: incorporatelatestmasterwithoutlosingrecords, finalrootchecks/indexfreshness, pushPR58/CI; mergefinaltips,verifyremotes/livepublication,cleanupowntaskbranches/worktreesandcompleteSteleTASK808/811/812. No live trade orstrategy-codechangewasmadebythisresearchtask.

## v64 - 2026-11-08 (Final integration checkpoint)

Integrated currentmasterc9359c4, including upstreamadaptive-rosterPR83 anddependency/CIupdates. Allupstreamrecordsretained; this task's originalrequests nowprompt47-48, continuation53-62. Rootowns onlyresearch/docs/routing/provenance/indexchanges. Sourcecodesharedfromupstreamisnotpartofthetrading-researchimplementation. Finalmergedunit/doc/indexchecksandremoteCIstillrequired; sourcebenchmarkreviewrechecksunchangedforecast_statsASTagainstits originalpinnedrevision. FinaldeliveryreceiptsliveinTASK808andcanonicalruncheckpointssofuturebookkeepingdoesnotcreateanunmergedpost-mergecommit.

## v65 - 2026-11-08 (Concurrent delivery integration)

Integrated mastera75f5b6 after concurrentfrontierPR81 andbotsPR84 landed. Preservebothupstreamfeaturesandallresearchrecords. EarliermanualCIond0ecd6awas canceledas superseded; finalCI mustrunafterthismerge. WebsitePR305merged96db35f08778ae752bd84e65554de9710e695b62 afterallchecks; actualproductionacceptanceunderway. No new researchorsemanticgate was rerun. Finaltasksource/instruction/indexverificationisnext; privatebackupsanddeliveryreceiptsarepreservedoutside sharedcheckout.

## v66 - 2026-11-08 (Continuation preservation verified)

Latestupstreammemoryhadreplacedearliertrend-filterandadaptive-rosterentrieswithitsnewfrontierentry. Restored both earlier acceptedrecordsfromd0ecd6a withoutchangingtheirbodytext; latestupstreamfrontierandbotspromptrecordsremainintact. Task-ownedrecordsfollowthepreservedhistorywithuniqueversions. Upstreampromptversion45duplicatesandmemoryversion28duplicatespreexistandremainuntouched. Finalcurrentdiscoverycounts900backtester,361extension,34mongo,860SolTUI; docsandindexfreshnesspassed. Sourceforecast_statsASTandengine/next-openfilesremainidenticaltothepinnedscopeaudit. Final900testlocalrunandremoteCImustpassonthefinalpushedtip.


## v67 - 2026-11-08 (Live publication and final local acceptance)

Currentintegratedbacktester900/900 passed; docsdiscovery900/361/34/860matchesinstructions,and sourceindexfreshnesspasses. EarlierCLI/browsersafetychecksandindependentall-assertionevidencebindingsremainaccepted. WebsitePR305merged96db35f08778ae752bd84e65554de9710e695b62; live-acceptance-verifier confirmedall24productionpage/JSON/Markdowndownloadendpointsandall110canonicalclaimsagainstthatexactdeployedrevision. Proof: canonicalruncheckpoints/website-live-acceptance.json. FullsuiteconceptualexitSATURATED-FRONTIERdoesnotmeanprofitabletradingorcompleteknowledge. RootPR58finalCI/mergeandownbranch/worktreecleanupremain; no furtherresearchworkerorserviceisrunning.

## v54 - 2026-11-08 (PR 46 and PR 58 integration)

Target: resolve and merge the two requested PRs. Stele tasks TASK-879, TASK-880, TASK-881.

Workspace: /Users/mitch/dev/solmargintrader-wt-01a1ba3b; private branch agent-01a1ba3b. Shared checkout and original PR worktrees belong to other sessions and remain untouched.

Completed: inspected PR heads and merge guidance; merged origin/master into PR 46; retained both workflow histories and automatically merged source and CI changes. Conflicts were limited to generated indexes and workflow records. Executor source remains unchanged from PR 46.

Verification: executor source exactly matches original PR head 00be663; 202 offline tests pass (5 network tests excluded); Ruff lint and formatting pass. Hash-index check passes. Docs counts currently read the pre-merge HEAD; rerun after the merge commit before interpreting count drift. All final-head GitHub CI checks remain required.

Remaining: regenerate indexes after staging resolutions, commit and push to executor-e1, wait for CI and merge PR 46; repeat against updated master for PR 58; verify both merge receipts and clean this private worktree. No trading or service restart is part of this task.

## v55 - 2026-11-08 (resumed integration)

Completed: PR 46 resolution was pushed at 6c1fc4b. Executor 202 offline tests, Ruff lint and format, docs counts, index freshness and unique paths passed. Seven CI jobs passed; SolTUI was running when concurrent PR 86 updated master to ea2d288 and caused new index conflicts.

Current: merge ea2d288 into this private branch. Only generated index files conflict. Resolve and stage before regeneration. PR 58 advanced to b899458; use that or a newer remote head.

Remaining: commit regenerated artifacts, push executor-e1, wait for all final-head CI and merge PR 46. Then integrate latest PR 58 against the landed master, verify all CI and merge. Preserve other sessions and their worktrees.

## v68 - 2026-11-08 (PR 58 conflict resolution)

Target: complete the original two-PR merge request and resume instruction. Stele TASK-879, TASK-880, TASK-881.

Completed: PR 46 merged by a concurrent session as 06a1f95347a835cdb2951bf2f043457104d74866. Its merged tree exactly matches our pushed 016a040. Seven final-head jobs pass; SolTUI is still running and must be verified. Executor source remains unchanged from original PR 46.

Current: merged origin/master 06a1f95 into latest PR 58 head b899458 in private worktree /Users/mitch/dev/solmargintrader-wt-01a1ba3b on agent-01a1ba3b-pr58. Conflicts affect generated indexes and workflow records only. Both histories are retained. No source or research receipt is rewritten.

Remaining: regenerate derived indexes after staging resolutions, verify docs and index checks, commit and push HEAD to agent-01a1b5ef without force. Wait for all final-head CI jobs, merge PR 58, verify both merge receipts and source/receipt preservation, then remove only our clean private branches and worktree. Shared checkout and original PR worktrees remain untouched.

## v69 - 2026-11-08 (Bots tab v2)

Target: prompts.md Bots tab v2 entry. Stele TASK-884. Branch feat/bots-tab-v2 in /Users/mitch/dev/solmargintrader-wt-39e8bf11.
Delivered before this: PR #84 (merged by another session while CI was red) and follow-up PR #86 (index regeneration), both on master.

Completed: `soltui/bots_screens.py` (coin picker, auto-optimize window with the SAVED / NOT SAVED popup and per-coin table); optimize run numbering with growing, non-repeating candidate lists (`candidates(bot, current, run, tried)`, history in `bots/optimize-history-<bot>.json`); per-coin stats; `hourly()` splices 1m-resampled history before the 1h file; `bridged()` fills gaps of up to 48 h; default backtest start is the start of usable data; `backtest_many`; `pricefeed.ensure_recorder` + LaunchAgent `com.mitchhudson.soltui.pricefeed` (KeepAlive, `record --wait-lock`); `prices.start`/`prices.stop` replaced by `prices.ensure`; one-row top fields.

Measured: DCA optimize runs 1-3 over 23 coins took 7.8 / 4.0 / 2.8 s; grid backtest from the start of data runs 2021-06-17 (SOL) and 2019-11-09 (BTC).

Remaining: after merge, fast-forward the main checkout and run `python -m soltui.pricefeed install` there so the agent runs the new code.

## v70 - 2026-11-08 (SessionStart hook JSON repair)

Target: identify and repair the Codex error "hook returned invalid session start JSON output". Stele TASK-892 (diagnosis), TASK-893 (repair), TASK-895 (verification and delivery).

Worktree: /Users/mitch/dev/solmargintrader-wt-01a1ba64; branch agent-01a1ba64; base origin/master 4d0f027. Original checkout has live concurrent sessions and unrelated dirty files. Preserve them.

Completed: read project instructions and prior hook failure records; isolate workflow records. The prior TASK-127 exit 126 issue is a different failure and does not establish the current cause. The hook specialist owns canonical implementation/config and test edits outside this repository. This repository changes only its required workflow records.

Constraints: reproduce actual registered SessionStart stdout; preserve enabled hooks and trust metadata; avoid restarting the shared daemon. Do not touch trading runtime, signing, services, research jobs, or unrelated work.

Remaining: finish diagnosis, repair canonical producer, install and verify output, run relevant checks, commit and merge task-owned changes, record delivery evidence.

## v71 - 2026-11-08 (Stop hook ownership repair)

Target: extend the hook repair to the recurring Stop block counting 336 shared-checkout paths. TASK-893 now includes both fixes. Keep legitimate checks on this session's own unshipped work. Preserve unrelated dirty files and active sessions. The canonical-hook specialist owns both implementation fixes; a separate read-only verifier inspects loaded daemon evidence.

Verification: workflow-only diff passes git diff --check and scripts/check_docs.py (2,155 discovered tests). index/build.py --check correctly detects changed workflow records; rebuild the offline index after finalizing these records. No trading code changed.

Remaining: diagnose/repair both hooks, verify installed behavior, deliver canonical source and these workflow records through passing PRs.

## v72 - 2026-11-08 (hook diagnosis confirmed)

Root cause: actual Codex 0.167.0 daemon registry enables adapter74c6161da6b220bd for memory-central-session-brief.py. That adapter exits 0 with 1,671 bytes of plaintext beginning "[memory-central] STALE:". Parsing stdout as JSON fails at line 1 column 2. The installed adapter /Users/mitch/.codex/hooks/claude_hook_adapter.py passes a single command output through without normalization. Canonical source is /Users/mitch/dev/codex-local-ai-setup/scripts/claude_hook_adapter.py. Preserve valid JSON and wrap plaintext SessionStart output in hookSpecificOutput.additionalContext with hookEventName SessionStart. Lesson KNOW-903 records this trigger.

Stop diagnosis: /Users/mitch/.claude/hooks/ship-it-stop.py attributes inherited dirty paths when a snapshot is absent, overwrites baseline on resume, and repeats identical blocks across turns. Lesson KNOW-902 anchors the concrete symbols. The current parent baseline already matches 337 paths, so preserve it; no blanket sweep or counter reset.

Implementation worktrees: /Users/mitch/dev/codex-local-ai-setup-wt-hook-json-20261108 (adapter) and /Users/mitch/dev/claude-wt-hook-json-20261108 (Stop hook). The specialist owns those source changes. A separate verifier captured actual loaded registry and reproduced the offending output.

Remaining: focused regression checks, install both canonical repairs, verify exact launcher and disposable ownership scenarios, deliver all task-owned changes through passing PRs, and complete TASK-893/TASK-895.

## v73 - 2026-11-08 (both hook repairs installed)

Installed: adapter v1.1.0 from canonical commit 757e2f7; Stop hook v1.1.0 from canonical commit 88d6933. Adapter wraps plain SessionStart context and preserves valid JSON. Stop preserves the original session baseline, excludes inherited ahead commits from a real SessionStart baseline, adopts unknown dirty paths without claiming them, and suppresses identical pending-work signatures across turns. New paths, changed files, and new commits still block.

Validation: 70 setup tests pass (including 8 new adapter cases); 65 hook-enforcement tests and installer checks pass. Guarded install with preimage backups/readback preserved config.toml, hooks.json and settings.json bytes; no daemon restart. Receipt: /Users/mitch/.codex/claude-migration/hook-repairs/session-json-20261108T090919255187Z/receipt.json. Installed adapter SHA256 5559368361c3fb3ad29d8dbb94db664d4f46f97786fc3d24ae7f7e0e054da5ff; installed Stop SHA256 af401be680327064ea4ef93573ba5c63526f3e1c2b30af7c5c220277123b4c40.

Delivery: Stop https://github.com/mithudso/claude-config/pull/33; adapter https://github.com/mithudso/codex-local-ai-setup/pull/11; repository workflow records https://github.com/mithudso/solmargintrader/pull/88. This repository changes only prompts, continuation records, and their offline retrieval indexes. Its documentation drift check passes; the offline index was rebuilt without inference/embeddings.

At checkpoint: independent installed acceptance and final CI/merges are in progress. TASK-895 tracks final receipts and completion; check its current state before resuming. Preserve unrelated staged herdr/context7 changes in /Users/mitch/.claude and all original solmargintrader work.

## v74 - 2026-11-08 (installed acceptance passed)

Independent acceptance: exact enabled memory-central launcher exits 0 and emits 1,814 bytes of valid SessionStart JSON with original context. Installed Stop subprocesses in disposable repositories allow inherited dirt/ahead commits, preserve snapshots on resume, block a new own edit, allow an unchanged repeat, block a later distinct edit, and block a new own commit while excluding inherited commits. A late baseline still checks ahead commits. Installed hashes match the guarded receipt.

Actual Codex 0.167.0 daemon retains enabled/trusted adapter and both Stop/snapshot registrations with no warnings/errors. config.toml, hooks.json, settings.json, parent baseline and parent hook counters remain unchanged. A subsequent ordinary UI turn has not been observed; exact installed command/runtime checks passed. No restart is needed.

Remaining at delivery checkpoint: merge the three linked PRs after final-head CI, confirm remote default-branch content, remove only clean task worktrees/branches, and complete TASK-895 with final merge receipts. The installed behavior is verified. No user decision is pending.

## v75 - 2026-11-08 (concurrent workflow-record integration)

Merged origin/master afaa03a after another active session delivered Bots tab v2 in PR 87. Preserved its prompt and continuation entry verbatim and retained every hook-repair record. Renumbered these hook entries after the incoming history. Rebuilt only offline retrieval indexes for the combined tree. No Bots or trading source was edited by this hook repair.

Canonical repairs are merged: Stop PR 33 as 79bc183c99a171d7221813724bbc10d6a85df7cd; adapter PR 11 as 4d385318438647bcddad9f368da927b5e9c9ada9. Installed acceptance already passed. Remaining: wait for final PR 88 checks, merge, verify remote content, clean only this task's worktree/branch, and complete TASK-895.

## v76 - 2026-11-08 (HTML mirror conversion; TASK-894)

Target: recursively convert HTML/HTM below /Users/mitch/dev/solmargintrader/tradingview/www.tradingview.com to text-only Markdown. Inventory: 31,880 HTML files, 9,371,462,657 bytes. Keep original HTML and generated mirror artifacts out of Git. Use Python stdlib and no network. Preserve headings, lists, code and table text. Remove scripts, styles, images and hidden markup; link labels remain text. Default output is a sibling tree; skip existing Markdown unless overwrite is requested. This extracts saved HTML, not content that requires JavaScript execution.

Worktree: /Users/mitch/dev/solmargintrader-wt-01a1ba63; branch agent-01a1ba63. Shared checkout has other sessions and unowned changes. Base updated from a75f5b6 to origin/master 4d0f027 in the private worktree only.

Remaining: implement converter and documentation; verify regression fixtures and representative local mirror files; refresh offline indexes; commit/push PR, pass checks, merge and verify remote default branch. Do not change the shared checkout or other worktrees.

## v77 - 2026-11-08 (HTML mirror converter verification; TASK-894)

Completed: scripts/html_to_markdown.py uses Python stdlib, preserves subfolders and textual Markdown structure, filters hidden/embedded payloads, detects encoding, preflights name collisions, publishes atomically, and supports skip/overwrite/dry-run. scripts/test_html_to_markdown.py has 11 passing behavior checks on Python 3.13 and system Python 3.15. Ruff lint/format, scripts/check_docs.py and offline index checks pass. CI runs the converter suite in its docs job. docs/SCRIPTS.md documents the command. Incoming Bots tab history from origin/master afaa03a is retained; no Bots code was changed by this task.

Execution: converted 31,880 files into /Users/mitch/dev/tradingview-markdown with zero errors; 11 outputs are empty (10 meta-refresh redirect stubs and the JavaScript-only chart page). A rerun skipped all 31,880 outputs. /Users/mitch/dev/tradingview-markdown/conversion-manifest.json lists every source/output, output hash, empty source and the final rerun summary. /Users/mitch/.local/bin/tradingview-html-to-markdown.py is an executable copy matching the repository script. Source HTML and the shared dirty checkout remain untouched.

Stele transport closed after initial lifecycle writes. Queued outbox operation IDs: 5c1ebafe, 8c704dd2, 9462ad7b, 56faab7b, 976096d2.

Remaining: finish merge/index commit, push task branch, create PR, pass final-head CI, merge and verify remote contents, record delivery receipt and remove only this task's clean worktree/branch. No source-conversion work remains.

## v78 - 2026-11-08 (HTML converter acceptance and concurrent delivery)

Independent live-acceptance-verifier confirmed all 31,880 output hashes, sizes, path mappings and UTF-8 decodes. The installed executable matches committed source SHA-256 c814d3e40f17a69d3c7f3a780a532b924f503b43774532ae6bab120a90a3e074. Actual --help and --dry-run succeed. The receipt is /Users/mitch/dev/tradingview-markdown/acceptance-receipt.json. Stele transport recovered; all five queued operation IDs in v77 were replayed.

PR 90: https://github.com/mithudso/solmargintrader/pull/90. Concurrent PR 88 merged as d355b694f3d56d7ab4ee0456691bf51c54352298 while CI ran. Retain all hook records, renumber converter entries after them, and rebuild offline indexes. Converter code and installed script stay unchanged. Current delivery checkpoint is /Users/mitch/dev/tradingview-markdown/conversion-memory.json.

Remaining: pass checks on the updated final head, merge PR 90, verify remote contents and clean only the converter worktree/branch.

## v79 - 2026-11-08: Base wallet discovery (TASK-911)

Worktree: /Users/mitch/dev/solmargintrader-wt-01a1ba75; branch agent-01a1ba75; base afaa03a. Preserve the shared checkout and all other worktrees.

Verified Base llms-full live: ETH uses eth_getBalance(address, latest), ERC-20 uses eth_call balanceOf(address); RPC alone does not enumerate tokens. Context7 cached pending/Flashblocks guidance is stale; current live docs explicitly prefer latest. Live baseline discovers ETH, USDC and gtUSDCp but Blockscout returns HTTP 403 and no other tokens can be discovered. The configured cdp CLI returns paginated balances successfully (100 rows on first page). KNOW-852 describes that existing indexed source.

Decision: use the configured cdp CLI for indexed balances, bounded pages/timeouts and sanitized failures, with public Blockscout/trusted RPC fallback. SolTUI must never load private keys or call unknown unsolicited token contracts. Preserve price confidence and airdrop exclusions.

Remaining: implement, focused regression tests, live acceptance and suite/docs/index gates, commit/push/PR/green CI/merge, verify remote content.

## v80 - 2026-11-08: Base wallet verification

Implemented in soltui/wallet.py, commands.py and tui.py: bounded configured CDP CLI balance pages, paginated Blockscout fallback, trusted/requested RPC balance checks, indexed provenance, safe malformed responses, conservative unknown-token exclusions and batched price URLs. No private keys or credential files loaded. CLI stderr is sanitized. Corrected AERO wallet-list address to the canonical address already recorded in docs/BASE-WALLET-QUERIES.md; liquidity configuration stays unchanged.

Verification: 12 new regression tests. 90 wallet/settings/integration tests pass; 73 wallet/Ethereum/UTXO tests pass. Independent live-acceptance verifier exercised the production _portfolio_scan handler with saved Settings: status ok, partial false; ETH 0.000558130650770097, USDC 1.0, gtUSDCp 77.44216571536937; 387 unrecognized rows excluded. Wallet compose/render shows those assets and indexed/exclusion labels. Full SolTUI suite running in /tmp/soltui-base-suite-01a1ba75.log.

Installation limit: /Users/mitch/.local/bin/soltui delegates to shared /Users/mitch/dev/solmargintrader at a75f5b6. Two running consoles have already imported old code. The shared checkout is held by other live sessions and has unrelated dirty work; do not change it or kill/restart their processes. Deliver the merged source; fast-forward the shared checkout and reopen consoles only after those owners release it. Avoid import overlays or silently retargeting the launcher.

Remaining: full suite/docs/index checks, final diff, commit/push/PR/passing CI/merge, verify remote content. Installed-console parity is not yet established.

## v81 - 2026-11-08: frozen Base wallet delivery checkpoint

Source delivery: https://github.com/mithudso/solmargintrader/pull/92 (agent-01a1ba75). Final CI and merge receipts live in Stele TASK-915 and the PR; query them before repeating delivery. The concurrent hook-repair records from PR 88 were preserved. The offline index was regenerated after resolving Git stages; duplicate-path check passes. KNOW-919 records the transient DuplicateKey failure from rebuilding before stages were resolved. No application bug remained from that generated-index issue.

Frozen independent acceptance: production _portfolio_scan with actual saved Settings and production Wallet renderer both passed in 9.35 seconds. ETH 0.000558130650770097; USDC 1.0; gtUSDCp 77.44216571536937; 387 excluded; 390 rendered rows; status ok, partial false, discovery complete, total complete, no errors. wallet.py SHA256 190d5046bd15c46c7d8dacc5e8ea4217170af536e9f373cc4aea89b73bf3afd5; tui.py SHA256 609b0a860c6c08f1c52dca36a9f06e587165517b52ae2225a9af1f6586bf6999. No files or services were changed by acceptance.

Local verification: 90 wallet/settings/integration tests and 73 wallet/Ethereum/UTXO tests pass; all 900 backtester tests pass; compileall, docs drift and index hash gates pass. Full-suite receipts are in /tmp/soltui-base-suite-final-01a1ba75.log and the PR's final-head CI. Use the final receipts rather than the terminated earlier run that observed a transient merge index.

Remaining product step: installed synchronization and fresh-console acceptance after shared-session ownership is released. KNOW-921 records the launcher/check-out mismatch. The source change is ready for remote delivery; preserve all unrelated original checkout changes and running consoles. Do not retarget launchers or use wallet-only import overlays. The live source behavior is verified; installed parity is a separate unresolved gate.

## v82 - 2026-11-08: final concurrent integration

Preserved PR 90's converter records and workflow history after origin/master advanced to eea27e2. Wallet, commands and TUI source hashes did not change in this merge. The final local full suite passed all 884 SolTUI tests (2 optional skips) in 709.185 seconds, and all 900 backtester tests passed. Stage resolved records before rebuilding indexes, as KNOW-919 requires. Source delivery remains PR 92; query its final-head checks and Stele TASK-915 for the merge receipt. Installed synchronization remains gated by other sessions releasing shared-checkout ownership (TASK-922).

## v83 - 2026-11-08 (TradingView card coverage, inventory)

Version: 83. Delta: v82 to v83; start TASK-886, TASK-887, TASK-888.

Target: reconcile all 114 built-in studies and local TradingView script/idea sources against existing cards and code. Create missing cards as spec-only, with source provenance and explicit rule gaps. Do not change executable registry or invent performance.

Worktree: /Users/mitch/dev/solmargintrader-wt-tv-cards; branch feat/tradingview-card-coverage; base origin/master 4d0f027. Original checkout has live sessions and unrelated dirty work and remains untouched.

Learned: prior PR 79 cataloged built-ins only. Local web mirror contains 742 script HTML pages and 1,609 chart HTML pages, plus 200 Markdown pages. Need canonical-URL deduplication and separation of actual indicator/method publications from market commentary/navigation. Stele KNOW-889 records scope and status constraints.

Remaining: source inventory, semantic/exact existence reconciliation, new cards and coverage validation, owning tests and indexes, commit/push/PR/checks/merge, final receipts.


## v84 - 2026-11-08 (TradingView cards, source review)

Version: 84. Delta: v83 to v84; author specifications and complete expanded inventory.

Inventory includes 114 built-in studies and 4,770 canonical source records: 747 script publications, 1,610 chart/idea publications, 2,323 help solutions, and 90 other exports. The help review selects 313 financial definitions. Explicit existence matches preserve 59 original cards and all 34 registry entries. Created 1,082 spec-only cards: 84 built-in signals, 600 custom script descriptions, 70 source-specific chart methods, 202 support definitions, 64 reusable methods, 47 library-function/group specifications, 12 named custom MACD/PPO variants, and 3 named-but-undisclosed strategies. No execution or measured status was invented.

Files: research/tradingview-card-coverage.json records hashes/excerpts/match reasons; docs/TRADINGVIEW-CARD-COVERAGE.md lists the cards and scope. scripts/check_tradingview_cards.py validates all references and optionally physical sources; CI runs its offline mode. Normalizer tv-description-v2 retains comparison operators and separates HTML block text. Raw dumps remain ignored. Source-limited cards explicitly retain missing formulas, parameters or future-post gaps.

Independent audit: research-contract-auditor reviewed 401 candidate chart titles and targeted full descriptions, 72 library definitions and 313 support definitions. It corrected holiday-art/platform false cards, undisclosed strategies, incomplete-source wording and hidden strategy omissions. KNOW-898 records concrete failures. It does not independently certify semantic completeness of every commentary page.

Verification so far: 1,141 cards parse, 1,082 new cards match ledger, all 114 built-ins covered; source re-binding and final independent audit in progress.

Continuation tooling is /tmp/solmargintrader-tv-cards: inventory.py, definitions.py, methods.py, generate.py, original publication extract and read-only audit artifacts. The committed ledger/cards are the durable products; generator scripts are session working material.

Remaining: complete full raw-source verification and independent review, run owning/integration tests, regenerate offline retrieval indexes, commit/push/PR/CI/merge, synchronize safely and record receipts. Preserve original checkout dirty files and other live sessions.


## v85 - 2026-11-08 (TradingView cards, final content)

Version: 85. Delta: v84 to v85; close expanded inventory and finalize 1,083 new cards (1,142 total).

All 114 built-ins have a card/code/alias disposition. 4,770 canonical sources and 4,890 physical source files are bound to source hashes and selected excerpt offsets. Added the independently found short-strangle method and corrected 29 non-OHLCV input requirements. Eight detailed chart strategies now retain their disclosed entry, filter, stop and management rules with additional bound source passages. Fifty-four new built-in cards also include official help clarifications. Named-only methods remain explicit source-limited specifications.

Initial local checks: backtester 900 tests had one search-fallback failure; focused SolTUI integration 97 tests had the same failure. Cause: repeating fees/slippage/carry in over 1,000 cards made slippage exceed the keyword index 60-percent document-frequency pruning cutoff, so that single-word fallback returned no hits. Reworded the shared cost instruction without altering the research risk requirement or search implementation. Rebuild the text index, then rerun both suites. No semantic embedding or inference runtime was started.

The new offline validator refuses duplicate new-card ownership, missing built-ins, stale implementation pointers, unrecorded cards and dishonest reviewed data availability. All four injected negative cases were refused. The full raw-source verification passed before final content enrichment and is running again. scripts/check_docs.py passed all 2,155 discovered test counts.

Remaining: final independent audit of the corrected content; refreshed offline retrieval artifacts; passing backtester and focused SolTUI integration; commit/push/PR/final CI/merge; safe default-checkout synchronization and final receipts. Original dirty paths remain untouched.


## v86 - 2026-11-08 (TradingView cards, verified)

Version: 86. Delta: v85 to v86; record final local checks and targeted review.

Completed content: 1,083 new spec-only cards; 1,142 total cards; all 114 built-in study dispositions; all original 59 cards and 34 registry entries preserved. Complete source inventory has 4,770 canonical records and 4,890 verified physical sources including the reference and excluded captures. docs/TRADINGVIEW-CARD-FILES.md lists every changed canonical checkout path.

Verification: backtester 900/900 pass (42.359 seconds); focused SolTUI background queue, Docs browser and Docs search integration 97/97 pass (33.896 seconds); scripts/check_docs.py passes 2,155 discovered tests; card CLI prints all 1,142 cards; all four negative validator injections are refused. Independent research-contract-auditor final targeted re-audit passed: 8 strategy summaries, 62 added source passages, 29 data metadata anchors, corrected exclusions/aliases and non-runnable status. Scope remains complete deterministic inventory plus targeted semantic review, not an independent semantic reading of every chart page.

Formatting gate found trailing spaces at bounded excerpt cutoffs. Card lines/EOF were normalized, corresponding excerpt end offsets were shortened, and full raw-source verification is repeated on the final artifact. No formula, source text, input requirement or status changed.

Operational incident: index/search.py --text slippage also calls idle.maybe_start and spawned this task worktree index/idle.py --run-build worker PID 88605. Stopped that exact task-owned process with SIGTERM after matching its full command. Pre-existing Ollama servers were untouched. Use INDEX_NO_AUTO=1 on all remaining checks/commits. The query correctly returns 173 keyword hits after shared boilerplate rewording. No search implementation changed.

Remaining delivery work only: commit/push current branch, open PR, record its URL, wait final CI, merge, verify remote content, and synchronize the default checkout only if unrelated active files remain intact. TASK-886 inventory and TASK-887 cards are done; TASK-888 owns delivery.


## v87 - 2026-11-08 (TradingView card delivery checkpoint)

Version: 87. Delta: v86 to v87; integrate concurrent upstream work and preserve both histories.

PR: https://github.com/mithudso/solmargintrader/pull/91 ; branch feat/tradingview-card-coverage. Initial catalog commit 776aedb. Integrated upstream d355b69, including Bots tab v2 from PR 87 and hook-repair records from PR 88. Their code and history are preserved; only derived indexes are regenerated. This task owns the card catalog and related validation/docs, not those other sessions' live services or hook installations.

Final card content is 1,083 new specs, 1,142 total cards, 114 built-ins and 4,770 canonical sources. The final raw-source checker verified 4,890 physical sources. Independent targeted audit passed and its formatting follow-up confirmed all corrected source spans. Ledger SHA256 b5a9049305179e6f69d7c591edb6c982c366129040215d6c6d176d07813ce9ca. No executable trading entry changed.

No further card implementation is required for this request. For delivery/resume, inspect PR 91: if it is still open, finish final-head CI and merge; if merged, use its merge receipt and complete TASK-888 if needed. TASK-888 holds the authoritative final delivery receipt. Recheck conditional remaining actions rather than replaying completed inventory or card extraction. Source-limited definitions are documented product limitations, not a pending permission request.


## v88 - 2026-11-08 (TradingView final integration checks)

Version: 88. Delta: v87 to v88; confirm merged-tree checks without changing card content.

Integrated upstream d355b69 in merge commit 67b2e5d. All 59 pre-existing cards match origin/master byte for byte. The task diff contains no SolTUI runtime, backtester/core, backtester/tests, liquidity, executor, extension or Mongo changes. The catalog source ledger remains SHA256 b5a9049305179e6f69d7c591edb6c982c366129040215d6c6d176d07813ce9ca.

Integrated checks: 97 SolTUI queue/Docs integration tests pass (29.510 seconds). The 900-test backtester run under INDEX_NO_AUTO=1 had 8 failures and 2 errors, all in the 20 mocked IdleTests whose purpose is to test enabled auto-indexing. The other 880 tests passed. Reran all 20 IdleTests with INDEX_NO_AUTO unset; all passed in 0.023 seconds, with process launch/network methods mocked and temporary paths. No background index process started. This is a test-environment interaction, not a product failure. The earlier complete 900-test run also passed before upstream integration. CI runs the full suite under its normal mocked-test environment.

Documentation discovery now agrees with the concurrent Bots changes: backtester 900, extension 361, Mongo 34, SolTUI 872; total 2,167. Default card integrity checker and full raw-source binding checker pass; source inventory is 4,770 canonical records over 4,890 verified physical files. All four negative integrity probes are refused.

Delivery continuation is conditional on https://github.com/mithudso/solmargintrader/pull/91 : if open, wait for final-head required checks and merge; if merged, verify its default-branch files and use the merge receipt in TASK-888. No more card implementation is required. Preserve the original checkout's unrelated changes and all other active PRs/worktrees.


## v89 - 2026-11-08 (large-catalog CI test setup)

Version: 89. Delta: v88 to v89; fix the five Docs editor test assumptions exposed by the expanded card catalog.

CI run 42467823348 on c09ecc9 passed backtester, docs, extension units/browser, liquidity and Mongo. Executor setup failed before tests after three HTTP 504 responses downloading uv 0.13.7. The macOS suite ran 872 cases in 747.928 seconds and had five StopIteration errors: Docs editor tests assumed soltui/config.py or research/results files would occur in the unfiltered first 1,000 alphabetically sorted rows. New strategy cards legitimately fill that first page.

Changed only those five test setups in soltui/tests/test_tui.py to use the real #docs-filter input before selecting late-sorted target files. Existing cursor/open/read-only/unsaved-editor assertions remain intact. The production table cap, filtering and editor behavior did not change. Full TestDocsTab now passes all 9 cases locally in 78.133 seconds. KNOW-923 records the literal failure and the reason. No card content or ledger provenance changed.

Final delivery stays conditional on https://github.com/mithudso/solmargintrader/pull/91 ; push this test/index correction and wait for a passing final-head CI run. The new run also retries the transient executor tool download. Preserve all other sessions and their active PRs. TASK-888 owns the final merge receipt and cleanup; no new strategy implementation is required.


## v90 - 2026-11-08 (card delivery: concurrent converter integration)

Version: 90. Delta: v89 to v90; integrate origin/master eea27e2 from PR 90 without losing either task.

Preserved all converter source, documentation, tests and history. The docs CI job retains both Offline HTML converter behavior and TradingView source-to-card coverage checks. Card content remains unchanged at ledger SHA256 b5a9049305179e6f69d7c591edb6c982c366129040215d6c6d176d07813ce9ca.

The five capped-catalog Docs editor fixture corrections pass all 9 TestDocsTab cases locally. Other preceding CI checks passed; the executor artifact download receives a new attempt with the final integrated head. Delivery is still through https://github.com/mithudso/solmargintrader/pull/91 and TASK-888. If that PR is already merged, verify its receipt rather than replaying extraction or test fixes. No card implementation or new source extraction is pending.


## v91 - 2026-11-08 (executor CI tool-download repair)

Version: 91. Delta: v90 to v91; repair the repeated external installer failure using an existing repository convention.

Executor CI failed in runs 42467823348 and 42469464071 before tests. setup-uv v5 tried https://github.com/astral-sh/uv/releases/download/0.13.7/uv-x86_64-unknown-linux-gnu.tar.gz and received three HTTP 504 responses in each run. In the same workflow, liquidity setup-uv v10.3.3 installed the same uv 0.13.7 in under one second from releases.astral.sh. Context7 official setup-uv documentation confirms the mirror-first download path with GitHub fallback.

Changed the executor setup-uv action to the exact v10.3.3 SHA already pinned for liquidity (68559e99cc807c1eb7e9238fd43a15bba460eec2). No executor code, uv.lock, frozen sync flag, test selection, runtime default or trading configuration changed. This is a necessary CI bootstrap repair, not a relaxed gate. The original 59 cards and all new card content remain unchanged.

Delivery: https://github.com/mithudso/solmargintrader/pull/91 ; TASK-888. Finish the final-head checks and merge if the PR is still open. If already merged, verify its receipts and preserve other sessions. No card source extraction or implementation remains.

## v92 - 2026-11-08 (TradingView cards: wallet integration)

Version: 92. Delta: v91 to v92; preserve concurrent Base wallet PR 92.

Integrated origin/master d596856 after PR 92 landed during final CI. Preserve all wallet code, tests and its installed-console limitations. Only shared histories and generated indexes require conflict resolution. The catalog remains 1083 new spec-only cards, 1142 total, with unchanged source ledger SHA256 b5a9049305179e6f69d7c591edb6c982c366129040215d6c6d176d07813ce9ca.

Delivery remains conditional on https://github.com/mithudso/solmargintrader/pull/91 and TASK-888. Complete final integrated-head checks before merge. Existing running consoles are owned by other sessions; do not restart them or retarget launchers. Preserve unrelated checkout changes and verify any safe synchronization independently.

## v93 - 2026-11-08 (script strategy understanding; TASK-929)

Target: explain the idea, objective and mechanics of each strategy publication in the saved script directory and create individual cards. There are 742 HTML pages here. Existing TASK-888 / PR91 covers a broader inventory of 747 canonical script publications, with 21 explicitly typed strategy, 666 study, 55 library, and 5 missing type. This pass starts with the 21 strategy publications; optional user clarification about including indicator studies remains pending.

Existing generic cards quote author passages but often lack publication-specific synthesis. Read complete ssrIdeaData descriptions and preserve exact provenance. Strategy templates must be identified as frameworks rather than invented entry edges. Source code is not assumed available from an open-source badge. Keep missing rules, parameters and performance as explicit gaps. Preserve registry implementations, measured cards, shared checkout changes and active PR91 ownership.

Worktree: /Users/mitch/dev/solmargintrader-wt-01a1ba63; branch agent-01a1ba63, base d596856. Stele search helper could not start on this account; direct graph records supply the context. Relevant decisions: KNOW-663 strict card schema; KNOW-620 status semantics; KNOW-889 source-specific coverage; KNOW-898 title-only extraction failures; KNOW-930 current purpose/rule boundary.

Remaining: read and interpret every in-scope publication; author grounded individual cards and evidence manifest; validate/audit; commit/push PR, pass final checks, merge and verify delivery. Keep existing PR91 work distinct and do not merge another task's unfinished PR.

## v94 - 2026-11-08 (strategy source interpretation accepted; TASK-929)

Read all21 complete strategy-typed descriptions (92,770 characters) and checked native metadata for all742 HTML publications: 666 studies,55 libraries,21 strategies. Optional broader-scope question received no answer; proceed with the stated21-strategy interpretation scope. Authored13 canonical card enrichments and8 companion tool cards, indexed in research/TRADINGVIEW-STRATEGY-CARDS.md. Tools remain outside the executable card loader. No order path, registry strategy or measured result changed.

research/tradingview-strategy-understanding.json binds the complete metadata inventory,21 card hashes,55 raw-source passages and68 normalized legacy passages. scripts/check_tradingview_strategy_profiles.py checks schema/status, card identity/hash, independent audit freshness, source inventory/native types and exact passage offsets; --source-root performs full local-source verification. The source script.content fields are empty. Independent research-contract-auditor reviewed all21 source/card pairs and passed the final corrected set: manifest SHA256 1d40b13ab4eb8976f7cf2f419aa70932c9c1aab45ea54e19342d14736724ecd5; card set SHA256 762c8b10551e660352147dd100d9187d3b1b27076e10fbe9797639fe132bbcaf. Receipt: research/tradingview-strategy-understanding-audit.json.

Corrected findings: the single-instrument Bitcoin martingale needs no point-in-time universe; gap non-fill confirmation must not impose an extra bar not established by the author. Preserve both fixes and the source limitations. Canonical cards are version1.1.0. Newly merged PR91 has a legacy validator requiring literal Version:1.0.0 and a stale martingale data_review; reconcile both during integration. Retain all prior coverage passages and card identities.

Checks:43 existing card tests pass; full-source and offline interpretation checkers pass; Ruff lint/format, docs drift and whitespace checks pass. CI runs the new offline interpretation checker. Portable, directly usable collection: /Users/mitch/dev/tradingview-strategy-cards/README.md, with its own checker and pure-stdlib card parser. Raw readings and authoring inputs remain outside Git at /Users/mitch/dev/tradingview-strategy-card-work.

Remaining: commit own checkpoint, integrate newly merged PR91 while preserving the13 enriched cards and both workflow histories, reconcile coverage metadata/validator version handling, regenerate offline indexes after staging resolutions, revalidate, push PR, pass final checks, merge and verify remote contents, refresh portable package and remove only own clean worktree/branch.

## v95 - 2026-11-08 (landed coverage integration)

Integrated origin/master 188d329 (PR91) while preserving all1083 source specification cards, existing executable implementations, coverage ledger and prior workflow histories. The13 overlapping cards retain this task's independently accepted1.1.0 content and all68 prior source excerpts. Eight companion tools stay outside the canonical loader. Preserve both CI evidence-check steps. Reconcile the legacy martingale input review to OHLCV and allow semantic card versions rather than an immutable1.0.0 literal. Then stage resolutions before regenerating indexes.

Remaining: revalidate the combined catalog, commit/push, pass final-head CI, merge and verify remote contents, refresh the portable package and clean only own worktree/branch.

## v96 - 2026-11-08 (integrated strategy interpretations ready for delivery)

PR91 is merged as188d329. Both coverage gates now pass together: the legacy catalog retains1083 added specifications and1142 total canonical cards; the new interpretation manifest covers21 publications with13 enriched canonical cards,8 separate companion tools,55 raw passages and68 retained normalized passages. The original accepted manifest/card-set hashes remain unchanged. The legacy coverage ledger is version1.1.0 with an explicit single-instrument OHLCV review for the martingale. Its validator now accepts semantic card revisions while requiring a Delta record; the previous1.0.0-only check was reproduced as a failure before fixing it.

Checks on the integrated tree:43 card tests pass; both offline source/card checkers pass; the new checker verifies all742 original HTML files and every cited source offset with --source-root. Ruff lint/format passes for the new checker; docs drift and exhaustive offline index freshness pass. No unresolved merge markers remain after regeneration. Both CI evidence gates are retained. Independent semantic audit remains accepted for the exact21-card set.

Remaining: commit this integrated checkpoint, push a PR, wait for final-head checks, merge and verify remote content, refresh the stable portable collection and its audit/continuation receipts, then remove only this task's clean worktree and branch. Shared checkout and other active sessions remain untouched.

## v97 - 2026-11-08 (all trading scripts, including indicators; TASK-929)

The user answered the optional scope question: All trading scripts, including indicators. The previous21-publication scope is now a completed subset, not the full goal. Review all742 saved publications, including666 studies and55 libraries, and create source-specific semantic cards or exact existing-card mappings for every trading-related item. Review non-trading exclusions from complete descriptions too. Preserve the accepted21-card set and its1d40b13a manifest hash.

PR96 currently checkpoints the21-card subset at e9931f4 and must not be called complete for the expanded goal. A merge of optimizer documentation a70d62f is in progress; only three generated indexes conflict. Finish that merge after staging source/record updates, regenerate indexes and keep the PR draft while expansion is active.

Use p2.1.0 orchestration for bounded, disjoint semantic-authoring batches and independent source audits. The user's standing commit/ship and exact prompt/memory-record requirements override the skill's generic no-git and output-format defaults. No external research, inference or indexing runtime is needed; source gaps remain gaps. Native Anthropic model labels are unavailable here; use the runtime Codex workhorse tier for synthesis and record the mapping. Keep raw readings in a gitignored task cache under the private worktree, with resumable per-publication checkpoints. Root owns helper/manifest/index integration; workers own their assigned semantic JSONL outputs and must not revert others.

Remaining: extract complete source descriptions for remaining721 pages; balance authoring batches; create and review per-script explanations; expand manifests/cards and coverage; verify all source/card mappings; deliver only after the complete expanded goal is covered.


## v98 - 2026-11-08 (expanded source authoring active)

The private worktree merged optimizer docs a70d62f and committed4f011b0. PR96 is draft for the expanded goal. Prepared immutable gitignored source-corpus.json for742 publications,21 protected and721 remaining descriptions totaling3,807,108 characters. The authoritative disjoint assignments and corpus hash are research/tradingview-script-profile-work.json. Three source authors own only research/tradingview-script-profiles/shard-a.jsonl (240 sources,TASK948), shard-b.jsonl (241,TASK949) and shard-c.jsonl (240,TASK950). They save original per-publication synthesis, exact raw-source evidence and full read ranges after every item. Partial helper validation is a draft structural check, not independent semantic acceptance.

The expanded interpretations will use separate documentation cards under research/tradingview-script-cards and an all-script index. Preserve the accepted21 files, manifest hash1d40b13ab4eb8976f7cf2f419aa70932c9c1aab45ea54e19342d14736724ecd5 and prior source catalog. Existing executable/measured cards and registry are untouched. Existing catalog links do not claim exact publication equivalence. Full-source exclusions retain reasons/evidence in the manifest. Trading-session parsers and financial infrastructure stay in scope even without a market edge. See KNOW951 for this architecture.

Remaining: finish all three authoring shards; independently read/review every new source/profile pair, including exclusions; repair findings; render all in-scope documentation cards; bind deterministic output to source/profile/reviewer hashes; validate source coverage and frozen21; run p stage9 sourced append and executed stage10 selfcheck; finish final-head CI, merge PR96 and verify remote delivery; refresh portable collection; clean only owned branch/worktree.


## v99 - 2026-11-08 (incomplete cards inside requested directory)

The user now requires every newly created incomplete card under backtester/strategy_cards/incomplete. All three authors received the readiness schema refinement and will backfill their earlier records. Independently review disclosed computation completeness, not merely spec-only status or absent code. Preserve complete mathematical indicators even without portfolio orders. Place incomplete expanded documentation profiles beneath backtester/strategy_cards/incomplete/publication-profiles so companion documentation does not enter the strict executable-card loader. Root owns the relocation and deterministic links.

Separate TASK941/PR97 is actively moving791 older generic cards while retaining292 usable specifications and59 originals. Do not merge or modify its unfinished branch. Once it lands, integrate its loader/coverage changes and preserve its readiness evidence. The13 accepted native-strategy enrichments overlap its baseline files; preserve their enriched text, update readiness bindings after review, and resolve locations without invalidating prior semantic approval. Accepted21 manifest/card-byte hashes remain the prior source-reading receipt; a separate location receipt can bind relocated unchanged bytes. No original checkout edits are authorized while the other live session holds it.

Remaining: complete all721 original explanations and readiness decisions; independently audit new profiles plus21-card readiness/locations; integrate landed PR97; implement correct incomplete placement and source/profile/review/path gates; final delivery remains conditional on full scope. Draft helper checkpoint9e84032 is pushed to PR96.


## v100 - 2026-11-08 (all742 source decisions drafted; reviews active)

All721 new profiles are individually authored and helper-valid, plus the21 accepted native-strategy subset. Authors TASK948/TASK949/TASK950 are done. Their initial scope decisions are227/218/227 in-scope and13/23/13 exclusions; these are draft counts, subject to independent corrections. All742 saved script.content fields are empty. Source descriptions may still disclose complete formulas or snippets. The first author checkpoint is pushed as d88802f on draft PR96. Root has already repaired seven shard-a records after independent findings; exact new hashes were re-reviewed and passed.

Independent research-contract-auditors own only research/tradingview-script-profile-audits/shard-a.jsonl (TASK954), shard-b.jsonl (TASK955), shard-c.jsonl (TASK956). Every full source/profile pair, including exclusions, requires review. The JSONL receipts are the authority for exact covered IDs, full read ranges, pending findings and stale hashes. These audits are still partial. Resume existing reviewers from their saved unread IDs after context limits; never mark unread sources accepted or stop the user goal at a sample. The complete-source requirement and owner-required completeness refinement take precedence over p's default dispatch cap; record actual continuations and degraded/capped stage accounting honestly.

A key correction is KNOW972: do not mechanically copy missing_information into blocking readiness.gaps. Missing feeds/cache, current compatibility, full code parity or portfolio trade rules alone do not invalidate a disclosed independent indicator/output calculation. Conversely hidden core inputs/algorithms stay incomplete. Parent has read and repaired4KIgeLGo FINRA,XUX5VVN0 event decoding,EtM15SgP MA3D,Rhj1nNLH absolute drawdown,SWWMsMQw panel,ygNO2G1V tick candles,vdzfb2WA quality fields. Auditor passed their exact updated records. Other pending revisions are enumerated in the audit JSONLs; read those rather than reconstructing queue messages. Parent may apply concrete independent-review corrections, verify relevant source facts, then obtain a fresh exact-hash review. Do not bulk relabel from keywords.

TASK957 native21 completeness review is authored and mechanically corrected: research/tradingview-strategy-card-locations.json SHA25608568f361f90dfdc9ab12b116246ac64e237b170c785b70c449ddb10d2a68ecf,10 narrowly usable principal outputs and11 incomplete. All source/card bytes, full-read ranges and evidence offsets were reviewed. card_location() resolves21/21 after changing the reviewer's enum usable to usable-specification. Physical moves are NOT applied yet. The receipt is untracked until integration. Its existence makes the old file gate expect the final paths; apply moves before claiming that gate passes. Preserve accepted manifest1d40b13a and card bytes; location receipt is the overlay.

PR97 independently merged as8ed41ad61c731f52a157054790520e3dfc7f23a1 at11:46UTC. Fetch/integrate origin/master, preserve its791 relocations/readiness work and all other sessions. Preserve this task's13 enriched card bodies during rename/modify resolution. Apply the separately reviewed native21 final paths, reconcile affected global readiness rows/hashes/dispositions/counts and retain both validators. Incomplete new documentation cards live beneath backtester/strategy_cards/incomplete/publication-profiles; incomplete native companion tools beneath incomplete/native-strategy-profiles. Usable companion documentation remains under research.

Remaining: finish all three source audits and repair/re-review every finding; integrate landed PR97 and native moves; render all final cards; bind and verify full coverage/source/profile/review/card/path hashes; p sourced llms append and executed selfcheck; final CI/merge/default-branch receipts; refresh the portable collection and remove only owned branch/worktree. Portable README/memory now explicitly say expanded work in progress, not21-card task completion. Never touch the shared dirty original checkout while another live session owns it.

## v93 - 2026-11-08 (Four-child /dr start)

Active: TASK-905; research stage TASK-907, install stage TASK-908, publication/delivery stage TASK-909.
Workspace: isolated task checkout; branch agent-01a1b5ef; base afaa03a.
Scope: standard-depth /dr on Conditional nonlinear information transfer; Finite-sample dependency uncertainty; Lag-selection multiplicity; Directed graph preservation. Parent: Uncertainty-aware nonlinear crypto lead-lag. Prior TASK-808 is complete; reuse exact parent evidence without claiming this explicit child depth was already done.
Constraints: research only; no trades, keys, services, broad source rewrites or shared-checkout edits. Three independent source origins per concept; negative searches; exact readable source spans; deterministic and semantic research-gate/v4 checks for all assertions; preserve paid supported judgments. Do not infer executable SOL profitability from dependence, significance or graph stability.
Completed: read routing and /dr instructions; semantic hub lookup found parent claims and reference; verified shared checkout contains unrelated work; created isolated worktree from fresh origin/master. Research worker owns only canonical new run and its evidence; root owns project records, installation, audit and Git delivery.
Remaining: actual research/gate; qualified installed skill; finish tree/site projections; independent audit; tests, exact owned commits, PRs, CI, final merges and owned cleanup.

## v94 - 2026-11-08 (Four-child evidence accepted)

Completed: actual standard-depth native adapter adaptive research on all four named children. Forty-nine structured claim records (13 conditional, 13 finite-sample, 7 lag-selection, 16 graph) and 24 auxiliary assertions passed the final research-gate/v4: 56 SUPPORTED and 17 nonassertions. Packet SHA: 80027ebbee91025d1506d54460828fdc6d1a6e22d079d8ad735a12055803d8db. Validation SHA: 3edae8b09ac3f75c47e8ffaed95d898bb817db75ee8bf3f3e0b95c81f845c30c.

Independent source review: three original research groups per child, negative searches, 81 structured evidence spans and 32 bound snapshots. One bounded combined repair fixed seven first-review failures and six context gaps, with overlap between them; 60 judgments reused and only 13 changed pairs reviewed. Scientific statements and sources remain scoped to their actual studies. No measured five-minute SOL strategy is established.

Root report reproduces ten exact accepted assertions and labels the experiment proposal. Its identifiers were rebound to the final packet after two source-span repairs changed canonical IDs. Public-safe selected claim index and gate receipt are in research/nonlinear-lead-lag-children/. Raw sources and judge transcripts remain private in run nonlinear-lead-lag-four-children-task905.

Checks: 872 SolTUI tests ran (870 passed, 2 skipped); 34 Mongo tests ran (17 passed, 17 server/driver skips); 361 extension tests passed; offline oscillating dry run closed one positive round trip. Archived figure check passed 1084 transcription/recomputation checks, not a new market experiment. Initial 900-test backtester run had only the expected index-staleness failure from changed workflow records; regenerate the offline index and rerun after final documentation.

Stele transport closed after stage creation. Exact lifecycle writes queued: claim TASK-907 in 5e16424f; complete TASK-907 in 5532828f; claim TASK-908 in 509bdd0d. These identifiers are recovery receipts, not confirmed graph closure.

Remaining: finish supported skill render/metadata qualification and delivery; exact stable runtime activation; adapter finish and four child projections; independent publication audit; final root records/index checks, PRs/CI/merges and owned cleanup. Preserve original dirty checkouts, shared index differences and paused services.

## v95 - 2026-11-08 (Four-child delivery checkpoint)

Research and implementation work complete: all four concepts passed the accepted v4 gate and independent source/root-synthesis audit. The supported canonical finish returned COMPLETED with no warnings, 39 calculated minutes, artifact SHA a5f5ac0e6ea2cad3a7f562cccf5e0b370cca0849b1647b944236df520f5dea27. Five new nodes per target are four children plus their aggregate. Private tree 2866 to 2871; repository tree 2709 to 2714. The aggregate sits under Uncertainty-aware nonlinear crypto lead-lag. Four child aliases resolve to their own concepts.

Skills PR 92 merged as b5085dfc3ca6979079e34eae9972e2cd242ae5cd. Exact guarded source/loaded activation and stable supported rerender reproduce reference SHA 960ca20a8a07dfe87b34305b8469a9533906491849baece0504a933ab9c6c11f. Source hub 1.7.2 and loaded hub 1.6.2 retain their intentional route/model/SKIP differences. Three fresh skills/list samples passed. The scoped registry added exactly two descriptions, preserving all 1822 prior rows, and the new spoke ranked first. One failed route query used a venv without NumPy; a bounded retry used the existing global hub venv. No installation was needed. Ordinary task-scoped loading of the installed mxbai model on an already-running endpoint preserved Qwen; no server/pool/default/download/forced-unload change occurred.

Canonical completion emitted five packs per target and fresh reader/tree/context/facts data. Existing public search-index.bin bytes are unchanged; semantic metadata retains 1018 existing rows and adds no embeddings. Site typecheck and 2854-page build/publication policy passed. Website tests/privacy review and remote delivery continue independently; inspect actual receipts before claiming them complete.

Concurrent hook and HTML converter changes from origin/master eea27e2 are integrated. All incoming prompt/memory bodies and the prior baseline remain intact. This task's records were renumbered to prompt 54 and memory 79/80; preservation proof is in checkpoints/root-concurrent-record-preservation.json. The incoming duplicate prompt53 headings remain historical; no broad history rewrite was performed.

Required source-library reconciliation completed without errors. The stock helper maintained 8315 pending library-wide text-index rows, 22748 total. This was not a cohort-only row count or a semantic refresh. Raw source proofs remain unchanged.

Tracker fallback: additional exact writes queued in 6892023a (complete TASK-908) and 21e256d6 (claim TASK-909), alongside the earlier IDs. Graph closure is not inferred from queued writes.

At this source checkpoint, remaining actions are local final offline-index/document checks, root PR/CI/merge, website independent publication review/PR/CI/merge, production acceptance and cleanup of this task's clean merged worktrees. No further research or code implementation is planned. The authoritative final status and exact next action live in private run nonlinear-lead-lag-four-children-task905, checkpoint final-delivery (JSON). Read that receipt before resuming a stage; completed gates and source discovery must not be rerun.

## v96 - 2026-11-08 (Final root checks and delivery)

Final local checks passed: 900 backtester tests; 872 SolTUI tests ran with 2 skips; 34 Mongo tests ran with 17 server/driver skips; 361 extension tests; 11 converter tests inherited from the concurrent merge; positive offline oscillating round trip; 1084 archived figure checks; documentation drift and offline retrieval-index freshness. No new market experiment or live execution was performed. The final record-only change is followed by offline index regeneration and its targeted index tests; final-head CI remains the delivery gate.

The root report and selected claim index remain source-audited. The root run report adds only verified skill activation and supported canonical-completion metadata, and separates remote publication status. Final delivery receipt remains authoritative for downstream checks, exact remote commit pins and cleanup. Remaining: push final root branch/open PR, pass final-head CI, complete website delivery and live verification, merge the final pushed root tip, remove owned clean merged worktrees, then write final private receipts and tracker closure.

## v97 - 2026-11-08 (Public metadata privacy correction)

Independent final-delta review found operator-specific paths in this task's new public continuation metadata. Replaced only task-owned auto-authored paths with a neutral run slug, checkpoint identifier or isolated-branch reference. The exact user request, all incoming history and all scientific assertion text remain unchanged. Private pre-redaction snapshots and exact metadata-change receipts remain in the private run. Offline retrieval indexes are regenerated after this correction. Website workflow records receive the same scoped correction before the final merge.

The original root CI executor job failed before tests because setup-uv's release-binary download returned HTTP 504. GitHub could not rerun that job while the run was active. The required metadata correction creates a legitimate fresh final tip; all required checks must pass on that tip. No trading or research source behavior changes for this correction.

## v98 - 2026-11-08 (Wallet integration and CI bootstrap repair)

Incoming Base-wallet discovery fix PR 92 landed as d596856 while this task's CI ran. Integrated its code, tests, documentation and complete workflow history without changing its behavior. This task's sanitized record headings were renumbered after the incoming history. Earlier local SolTUI results qualify the earlier source tree; final merged-tree CI is required for the new wallet tests.

The executor CI job failed before tests with setup-uv v5: its GitHub release-asset URL returned HTTP 504. The liquidity job in the same workflow passed using the already-pinned setup-uv v10.3.3, which downloaded the identical uv 0.13.7 from Astral's official mirror. Local HEAD probes returned 504 for the old URL and 200 for the mirror. KNOW-935 records this concrete failure and the narrow repair. Align only the executor installer with that existing pinned action; retain frozen dependency synchronization, Python 3.13, both Ruff steps and pytest. No trading behavior or dependency lock changes are part of this repair.

Remaining: final index/config checks, final push and complete merged-tree CI; website managed CodeQL bundle downloads must recover before its final CI/merge. All scientific assertions and both metadata privacy corrections remain accepted. Read the private run's final-delivery checkpoint before resuming completed research or publication checks.

## v99 - 2026-11-08 (Catalogue integration before final delivery)

The complete root CI run 42471525856 passed on source 8265776, including the current 884-test SolTUI suite. Before merge, concurrent TradingView catalogue PR 91 landed as 188d329 and overlapped the common records and derived indexes. Integrated all incoming catalogue files, tests, coverage checks and exact workflow history. This task changes no incoming component implementation.

PR 91 independently landed the same mirror-capable executor installer already validated on this branch. Retain its workflow byte for byte, including the new card coverage check; this research PR now has no CI workflow behavior delta. The earlier installer investigation remains historical evidence in KNOW-935. Regenerate only offline retrieval artifacts for the combined source and run the catalogue coverage check, documentation check and targeted index/UI tests. Final pushed combined-tree CI remains required.

Website PR 307 merged as 26ed830f8255428a9406e6270be82be55194ae97 after its final checks passed. Production acceptance is separate and continues against that actual merge. All accepted scientific statements, canonical IDs, source bindings, installed reference bytes and public metadata privacy corrections remain unchanged. Resume only remaining delivery actions from the private run's final-delivery checkpoint.

## v100 - 2026-11-08 (incomplete card separation)

Version: 100. Delta: v99 to v100; start TASK-939 review, TASK-940 relocation, TASK-941 delivery.

Target: review the1083 cards added in PR91, keep substantive implementable specifications, and relocate cards with undisclosed/vague mechanics under backtester/strategy_cards/incomplete. Preserve all59 older cards, registry34, source evidence and unrelated dirty work. No new trading implementation is authorized by this sorting request.

Worktree: /Users/mitch/dev/solmargintrader-wt-card-triage; branch feat/tradingview-card-triage. Shared master is188d329 with337 unrelated dirty/untracked files. Concurrent PR96 enriches13 canonical cards and adds8 companion tools; integrate that delivered work without discarding its improvements.

Classification must inspect actual equations, code and mechanism text, not just spec-only status or numeric inputs. Asked whether complete indicator formulas without order rules should remain; default is to keep complete computable signals while flagging their absent runner. Classification decisions and unknowns must be explicit.

Remaining: classify every new card, independent review, move incomplete cards without loss, update catalog/ledger validation and references, relevant tests and source gates, commit/push/CI/merge, safe canonical sync and own-worktree cleanup. Use INDEX_NO_AUTO=1 on searches to preserve paused indexing.

## v101 - 2026-11-08 (card readiness clarification)

Confirmed user clarification: keep complete indicator specifications even without buy/sell rules. Retain a reproducible calculation with declared inputs; move names, generic descriptions, ambiguous predicates and undisclosed algorithms. Three research-contract reviewers each own361 cards, with exact evidence/gaps per decision under /tmp/solmargin-card-triage. Coverage validation will include both directories; the existing flat runtime loader naturally excludes incomplete/. Seven behavior checks pass for loss, duplicate, stale review, location and quote binding. Source/card bodies will not be rewritten during relocation. Remaining: assess all review results, reconcile concurrent PR96 enriched cards, relocate, final verification and delivery.


## v102 - 2026-11-08 (reviewed card relocation)

Version: 102. Delta: v101 to v102; complete TASK-939 and apply TASK-940.

Reviewed all 1083 PR91 cards in three361-card source-text batches. Cross-review covered188 initial keeps and120 math-bearing incomplete candidates. Parent accepted6 downgrades and10 upgrades. Final:292 new usable specifications remain active;791 incomplete cards move under backtester/strategy_cards/incomplete. All59 original cards remain active; active catalog351 and total1142. Every card byte is unchanged from the188d329 baseline. Registry34 is unchanged.

research/tradingview-card-readiness.json records each disposition, exact card quotes, narrow functional scope, SHA256, path and gaps. The owner confirmed complete indicator specifications should stay without buy/sell rules. Independent principal outputs/explicit selectable branches can qualify despite incomplete sibling features; hidden intermediate equations do not qualify. Runtime status stays spec-only.

Coverage checker now audits both directories and validates the readiness bindings. Existing flat runtime loading excludes incomplete/. Seven behavior checks pass for loss, duplicate location, stale review, wrong location and unbound evidence. Docs and the old extraction-file receipt preserve source coverage and relocated paths.

Remaining: finish full raw-source and relevant suite checks, update offline indexes, preserve incoming PR95/PR96 histories and any enriched canonical cards, commit/push/PR/final CI/merge, canonical read-back and own-worktree cleanup. TASK-941 owns final delivery. Do not rerun /tmp/solmargin-card-triage/apply.py after relocation; its one-time assertions intentionally refuse a second move. Existing and new card hashes are in /tmp/solmargin-card-triage/card-baseline.json. Shared checkout preservation snapshot contains337 unrelated paths.


## v103 - 2026-11-08 (incomplete cards, verified checkpoint)

Version: 103. Delta: v102 to v103; finish local gates and preserve incoming PR95.

Completed:791 byte-preserving relocations;292 new usable specifications plus59 original cards remain active (351 active,1142 total). Original card/registry contracts remain intact. All4890 raw-source bindings pass. Seven separation-integrity cases pass. Backtester880 guarded cases pass in28.177s; all20 mocked IdleTests pass separately in0.016s with INDEX_NO_AUTO unset, for900/900. SolTUI queue/Docs/coverage/editor selection100 cases pass in93.868s (one optional skip). Documentation counts agree on2179 tests. Targeted Python lint and both working/staged whitespace gates pass. Only offline keyword indexes were regenerated; no inference/runtime/index worker was started.

Integrated origin/master a70d62f from PR95 without modifying its optimizer source-context files. Shared histories and all other active PRs/worktrees are preserved. Concurrent PR96 remains its owner's unfinished branch; do not merge or rewrite it. If it lands during this delivery, preserve its card improvements, re-review affected content and update location/hash bindings before finishing.

Final delivery is tracked by TASK-941 and branch feat/tradingview-card-triage. If its PR is open, finish final-head CI and merge. If already merged, verify the remote receipt and complete TASK-941 if needed. Do not repeat extraction or the one-time move script. After actual merge, safely synchronize canonical master only when incoming paths do not overlap unrelated changes, verify all337 preserved path bytes, repeat focused fresh-process catalog/Docs acceptance and remove only this task's clean worktree/branch.

## v104 - 2026-11-08 (readiness concurrent research integration)

Version: 104. Delta: v103 to v104; preserve PR94 research work.

Integrated origin/master 0b46a88 after concurrent PR94 landed while this task opened PR97. Preserve all research artifacts and histories; regenerate only shared indexes after resolving Git stages. Card contents and the292/791 readiness decisions are unchanged. PR97 and TASK-941 own final CI, merge receipt and cleanup. If already merged, verify that receipt instead of replaying review/moves.

## v105 - 2026-11-08 (canonical incomplete directory correction)

The owner requires the actual canonical incomplete directory immediately. Earlier moves existed only in the private worktree pending CI. Apply only the reviewed791 byte-preserving card moves and incomplete README to the canonical directory now; preserve other edits and keep commits in the private branch. Snapshot task-owned changes separately from337 unrelated files. Reconcile these exact staged/unstaged moves safely when final delivery fast-forwards master. Save this correction in the committed prompt/history; final CI must cover its final pushed head.


## v106 - 2026-11-08 (landed readiness integration; full-source audits continue)

Integrated PR97/8ed41ad after it merged. Git preserved all21 accepted card byte hashes across its renames. Applied the separate21-card location receipt (10 scoped usable,11 incomplete) and rebound the13 canonical readiness entries to their enriched bytes. All other classifications are preserved. The catalog now has294 retained new/789 incomplete/353 active total; all1142 remain preserved. The broad catalog retains1142 total cards and59 original active cards. No executable registry or measured result changes.

All721 new source profiles are drafted; audits remain partial and authoritative coverage lives in the three audit JSONLs. Original authors repair bounded review findings in their own profiles (TASK978 batcha15findings; TASK979 batchb16findings), then independent reviewers recheck exact changed hashes and continue unread descriptions. Never stop at a partial context boundary. Index regeneration must wait for active profile writers and stage source resolutions first. Final full-scope publication, package refresh and remote delivery remain pending.


## v107 - 2026-11-08 (status question; original goal continues)

User asked So what're you doing now? Answered in commentary with actual partial progress, without claiming completion. All742 source decisions are drafted;21 native-strategy cards are independently reviewed and physically sorted in this worktree. At the status reply, audit coverage was556/721 expanded profiles. Exact current coverage/findings remain in the three audit JSONLs. No pause or scope replacement was requested. Finish the remaining reviews, bounded author repairs, exact-hash rechecks, final rendering and delivery.

Current integration gates pass: native21 full-source check verifies742 HTML captures and all raw/legacy/relocation evidence; broader catalog check verifies4890 local source files and353active/789incomplete/1142total cards. Fifteen script review/relocation tests and43strategy-card tests pass. Merge commit is pending only because two generated Markdown lines needed whitespace cleanup; regenerate indexes after staging their corrections. No canonical shared checkout edit occurred.


## v108 - 2026-11-08 (batcha fully accepted)

Batcha TASK954 is independently qualified:240/240 current profiles pass,1,269,027 source characters read,all13 exclusions reviewed,40 historical findings resolved with history retained. TASK989 repaired17 last findings without changing223 already accepted hashes. Current batcha profiles are227 in scope (45 usable principal specifications,182 incomplete),13 excluded. Root reran the full audit gate successfully. Preserve this accepted shard; do not reread or rewrite it without a new source/profile change.

Batchb/c full-source audits continue toward their tails. Their exact current coverage and revise queues are in the owned audit JSONLs. Original authors handle bounded repair tasks, independent reviewers recheck exact hashes, and only then qualify. TASK979 andTASK984 repaired23 batchb records; all23 have independent approval. No full b/c acceptance is claimed yet.

Ten current source profiles quote lines with trailing spaces/tabs. The renderer now normalizes quote display line endings and trims only trailing presentation whitespace; raw exact quotations and offsets remain unchanged in the manifest. A red-to-green fixture proves display cleanup preserves the raw evidence string and indentation. Nine review/placement tests pass. Final card rendering remains blocked by unfinished semantic reviews, not source inventory.


## v109 - 2026-11-08 (user clarified complete means standalone coin test)

All742 descriptions are read and checked. Expanded audits qualify all721 current source interpretations; native21 source QA is separately accepted. The user asked whether each card by itself can run calculations for a specific coin test. Answered No: documented components are not complete coin tests. No new card has a qualified standalone coin-test contract or runnable implementation. All691 source-profile cards now belong beneath backtester/strategy_cards/incomplete, with source disclosure kept separate from coin-test readiness. Do not present the208 disclosed source components as208 complete coin tests.

Root changed placement and labels mechanically without changing any independently audited semantic JSONL or frozen native card bytes. Native location receipt1.1.0 carries coin_test_ready:false for all21 and preserves the old source-computation judgments. All13 enriched canonical cards are incomplete; global legacy catalog remains1142 total with347 active/795 incomplete. The unrelated legacy catalog retains its earlier source-calculation criterion and is not certified runnable.

Remaining: final render/whole-source gates, publish portable collection immediately, finish exact-head CI/merge/remote verification and clean only own worktree. Do not reopen content review or imply coin-test implementation was delivered. Source interpretation/card creation can be delivered; standalone coin-test development remains unimplemented.

## v106 - 2026-11-08 (EPIC-980 research start)

Version: 106. Delta: v105 to v106; preserve the new two-track research request and exact run-start frontier.

Active: TASK-981 frontier research and TASK-982 full-suite bots under EPIC-980. The parent has18 unresearched child labels; four broader children already accepted by TASK-905 remain frozen. /dr standard depth applies; full-suite uses CFE maxRounds3, threshold3.2 and no default concept-count cap. Ample Firecrawl is authorized. Source-sharing cohorts, exact source spans and research-gate/v4 are required.

Canonical private continuation: /Users/mitch/.global-ai-hub/research/trading-research-epic980/memory.md and frontier-inventory.json. Bot track owns its private namespace. Root worktree: /Users/mitch/dev/worktrees/solmargintrader-trading-research-epic980. No trading, backtest or risk-configuration change is requested.

Remaining: source-backed child research and bot family exploration; claim gates, skills/packs/rollup, optimization/indexes and registration; serial Git/publication delivery and final live acceptance.
## v106 - 2026-11-08 (SolTUI card visibility)

Target: make retained strategy/indicator cards visible on Strategies. Diagnosis at8ed41ad: actual canonical launcher and fresh mounted app load correctly, but strategies.list/history enumerate REGISTRY34 and omit all292 new retained specs from351 active cards. Implement a unified filterable card table with explicit status; stable row keys preserve registry actions and readable names; nonregistered specs open their card and cannot be added/backtested. Keep791 incomplete cards excluded and all registry/trading defaults unchanged. TASK-971 owns implementation; verification/delivery use their tracked tasks. Worktree /Users/mitch/dev/solmargintrader-wt-card-ui, branch feat/soltui-card-catalog. Preserve337 unrelated canonical paths and other active UI/research branches. Use INDEX_NO_AUTO=1 for searches/acceptance. Save exact tested source revisions before safe canonical installation; do not restart existing consoles. Remaining: implement, behavioral tests, fresh UI acceptance, docs/index checks, commit/push/CI/merge, safe canonical sync and cleanup.

## v107 - 2026-11-08 (visible card catalog implementation)

Implemented strategies.cards as a read-only active-card catalog; existing strategies.list/history remain registry-only. Strategies now defaults to all351 active cards including292 retained TradingView specifications, with text/scope filters, status/data labels and card opening. Stable row keys preserve existing registry IDs and source opening. Specifications have disabled Add/Backtest selected controls plus keyboard/programmatic refusal. All/untested sweeps still use executable APIs. No card contents, registry entries or trading behavior changed.

Seven Strategies widget tests pass in40.144s,33 command/history/help cases pass in26.900s,13 mounted history/roster/bridge cases pass in57.671s. Additional Docs/glossary and full884-test SolTUI runs are in progress. Targeted lint/whitespace pass. Preserve HEADER_GLOSSARY public re-export for existing tests/importers. No test count changed; expanded actual UI tests verify catalog visibility, filter/card opening, incomplete exclusion and blocked execution.

Remaining: finish behavioral gates and independent fresh widget acceptance, safely install ONLY tested source files into canonical launcher checkout under fresh hashes (preserve all337 unrelated paths), record exact installed/source identities, regenerate offline indexes, push/PR/final CI/merge, safely reconcile pre-applied task files and clean own worktree. A later canonical install is authorized by the visibility fix; existing consoles must not be restarted. TASK-973 owns verification and TASK-974 delivery.

## v108 - 2026-11-08 (canonical catalog acceptance)

Independent private and canonical fresh mounted acceptance passed on source2442369: defaultAll351active rows including292TradingView cards, excluded791incomplete IDs, AveragePrice card/equation opens, specification controls disabled and keyboard/directUI/directcommand guards attempt zero queue or settings writes. Registered scope34; RSI source opening, fixture Add and selectedBacktest route preserved. strategies.cards351 while strategies.list/history34. Actual /Users/mitch/.local/bin/soltui wrapper resolves to canonical tracked launcher and venvPython. CanonicalHEAD remains8ed41ad until delivery; installed3sourcefile hashes bind loaded behavior to2442369.

Preservation/installation receipts: /tmp/solmargin-card-ui/shared-baseline.json (337unrelated paths), canonical-install.json (commands.py/help.py/tui.py exact before/installed hashes). Only these3task-owned canonical sourcefiles were pre-applied atomically after proving unchanged old bytes. Existing consoles/services were not restarted. Final source revision must retain the tested separate-runner wording correction, which has its own focused8.220s widget pass. All65earlier focused cases pass; full884 suite remains running. Test counts unchanged; lint/whitespace/docs/index gates pass before final metadata refresh.

Delivery is through branch feat/soltui-card-catalog and TASK-974. If the PR is open, finish final-head CI/merge. If merged, verify its actual receipt rather than replaying implementation. Update the canonical install receipt for the final3source hashes, preserve all337unrelated bytes/status, stage ONLY those pre-applied task paths before safe final fast-forward, repeat fresh canonical widget acceptance and clean only this task's worktree/branch. Do not overwrite concurrent UI/research work or restart live consoles.

## v109 - 2026-11-08 (full-suite catalog corrections)

The local full884-case suite completed in682.972s with878passes,4failures and2optional skips. Three failures were the new Refreshcards button missing BUTTON_COMMANDS and the old66-handler assertion; registered it as strategies.cards and updated the exactcount67. The fourth treated indicator titles such as1YearActiveSupply% as unlabelled return values. The safety check now binds only the strategy-title column to actual card labels; every result column retains its source-label checks. Six targeted bridge/percentage cases pass in5.021s. No trading/result-label protection was removed.

PR99: https://github.com/mithudso/solmargintrader/pull/99 ; final delivery TASK-974. Push these corrections and await final-head CI; prior24c063 CI must not be treated as final. The actual canonical UI already renders351/292 via the three verifiedpre-applied sourcefiles. Update only canonicaltui.py under its recorded hash to carry the routing-map correction, update canonical-install.json to final source identity, and preserve337 unrelated paths. No new runtime feature remains. If PR99 is already merged, verify its receipt instead of repeating implementation.

## v110 - 2026-11-08 (final visibility delivery checkpoint)

The local full-suite arithmetic is884cases:878passed,4failed,2skipped. The four integration assertions are corrected and all6targeted reruns pass. Final requiredCI will run the complete884cases. Product source is final; only this verification-count correction changes the next branch tip. PR99/TASK-974 hold final delivery receipts. Canonical3sourcefiles are bound by /tmp/solmargin-card-ui/canonical-install.json; preserve all337unrelated paths when reconciling them with the merged tree.

## v111 - 2026-11-08: optimization experiment workbench

Request: prompts.md v61. Tracking: EPIC-952; contracts TASK-953, implementation TASK-961, verification/delivery TASK-962.
Base: origin/master 0b46a88. Branch: feat/experiment-workbench-20261108. The shared checkout has 819 unrelated dirty paths and is held by other sessions. All changes stay in this task-owned worktree.

Plan and acceptance: docs/optimization-workbench-plan.md. Before code, recorded decisions in Stele: full immutable experiment/cell identity; spent final temporal intervals survive changed search settings; preserve all other active work, paused services and dry-run defaults. No live orders, daemon restarts, or research/index jobs.

Completed: source comparison, current architecture inspection, skill routing, clean private worktree, plan and common interfaces.
Remaining: implement foundation, native runner and UI/job controls; test failure/restart/holdout boundaries and import provenance; verify actual UI; refresh docs/indexes; commit, push, passing PR checks, merge and verify remote content.

## v112 - 2026-11-08: implementation active

Plan v2 adds exploration-exposure reservations before simulation. Changed window geometry must not turn explored dates into final holdout. Legacy optimizer history must be conservatively migrated or final validation refused; freshness is limited to tracked local evidence.

Workers share only this private worktree: foundation owns new experiments store/space/import/heatmap and tests; runner owns Bots integration/native runner and tests; interface specialist owns job lifecycle, screens, registry/UI/help and tests. Runner owns per-run and bot-finalization file locks. Root handles workflow/docs/indexes/release. TASK-953 complete; TASK-961 was claimed; TASK-962 was pending at this checkpoint. Context bundle written with p helper.

Remaining: worker implementations, independent correctness and loaded-UI checks, full relevant suites, docs/index refresh, remote delivery.

## v113 - 2026-11-08: integration review

All six source capabilities implemented in experiments.py, experiment_runner.py, experiment_jobs.py and experiment_screens.py, with thin Bots/registry/UI integration. Foundation initially25tests passed; runner now27regressions passed pluslegacy tests. Interface/process/registry tests passing; final combined counts pending final source freeze. New Python modules pass Ruff after scoped cleanup.

Independent review found and sent fixes for undated contributing import rows escaping comparison coverage, launch/failure transitions overwriting pause/cancel, and native negative vsTradingView positive drawdown. Canonical summaries/maps/comparison use loss magnitude while raw evidence stays intact. Runtime versions are frozen and checked on resume. True subprocess death/restart, config-save/report-crash recovery, historical edit with unchanged stat metadata and legacy-report-after-prepare were tested. Live verifier found a clipped adoption label at80columns; responsive fix in progress.

Remaining: verify final review fixes and loaded UI; full relevant suite, accurate doc counts and regenerated indexes; integrate current remote default preserving other work; commit/push, required checks, merge, remote content and cleanup receipts. No real data optimization, live orders, paused research or services were run.

## v114 - 2026-11-08: final source and acceptance checkpoint

The source was committed as 8726780 and the current default integrated as 1f72841. Concurrent incoming prompt/memory histories were retained. The task prompt is now v61; task continuation entries are v111 onward. Other sessions' working files were preserved.

All six features are implemented. Independent review reproduced and cleared three findings. Actual native CLI, detached worker controls, simulator results, CSV comparison and 80x24/160x55 headless UI passed. The actual Bots entry opened the workbench. The installed wrapper originally exposed 91 commands; verified feature code exposes 105, including 14 experiment actions. Synchronize installation only after final merge and preservation/overlap checks. No service restart is required.

The orchestration helper passed 8/8. The root llms facts/index received sourced additions and helper backups were removed. Consult TASK-962 for subsequent delivery receipts before repeating work. Preserve unrelated research JSON and untracked application files during default-branch sync.

## v115 - 2026-11-08: full verification passed

The complete SolTUI suite passed: 947 tests in 721.036 seconds, with two expected skips. Resource warnings were treated as errors. This includes 63 additional test cases. New Python modules and dedicated tests pass Ruff. Documentation counts agree: 900 backtester, 947 SolTUI, 34 mongo, 361 extension; total 2242. Offline repository index hashes agree. The card coverage validator and 11 HTML converter tests pass.

All six implementation capabilities, independent review fixes and actual loaded private-worktree acceptance are complete. Remaining delivery actions are required final-commit CI, merge, remote-content verification, safe default-checkout synchronization, installed-command parity and task-owned cleanup. TASK-962 holds the canonical live delivery receipt; this pre-merge record deliberately does not invent its own future merge SHA.

## v116 - 2026-11-08: sealed-history continuity verified

A final continuity check found that treating every old final reservation as permanently hidden blocked later rolling searches. The store now seals reservations atomically with the final verdict. Later exploration can use sealed periods as training history, while every other final test still refuses those spent dates. Active/paused/unsealed reservations remain protected. Exact own sealed reuse requires complete unchanged baseline/pick cells; new or replaced final evaluations are refused. Existing completed reservations migrate to the sealed state.

Six additional regressions include a five-coin rolling run, fresh later final validation, adoption with zero simulation calls, and historical mutation refusal. Final focused gate: 79 tests passed in 27.137 seconds; Ruff passes. Actual CLI, real simulator, detached controls and headless workbench acceptance were rerun successfully on the final store source, with stable hashes and no remaining fixture workers. The earlier 947-case full run passed before this bounded refinement; final CI covers the current 953 cases (69 additions). Documentation total is 2248.

PR: https://github.com/mithudso/solmargintrader/pull/98 . TASK-962 remains the canonical live receipt for final pushed SHA/checks, merge, remote content, safe installed-checkout parity and cleanup. Other active source edits were detected in the shared checkout; synchronization must preserve them and refuse overlapping changes. No services or live settings were restarted or changed.

## v117 - 2026-11-08: concurrent strategy-card integration

The final 880e188 CI passed all eight checks, including 953 SolTUI tests in 838.722 seconds with 14 expected optional-dependency skips. GitHub then refused the merge because PR 99 had concurrently advanced master to 3e5a9f3. That published Strategies browser work is preserved.

The private branch merged current master. Application hunks merged automatically. Generated indexes were reset only as intermediate regeneration inputs; both prompt/memory histories were combined and versioned. This task's prompt is now v61. A semantic test-count collision was corrected: the combined interface has 68 button handlers, rather than the 67 independently expected by each branch.

The integration specialist verified 45 targeted tests, the incoming strategy-card browser UI, and the actual combined app's Bots button, real workbench preview and dismissal. The combined registry has 106 commands, including 14 experiment actions; test discovery remains 953. The repeated full workbench acceptance binds the combined source hashes.

Remaining: regenerated metadata, checks on the final combined pushed tip, merge, remote content, safe default-checkout synchronization, installed command parity and cleanup. The shared checkout is now clean apart from its unrelated research/results/minute_coverage.json change. Consult TASK-962 for final receipts.

## v118 - 2026-11-08 (SolTUI v2 redesign mockup)

Target: prompts v62, Stele TASK-877, KNOW-878 (decision) and KNOW-883 (Textual/Rich lessons). Worktree /Users/mitch/dev/solmargintrader/.claude/worktrees/soltui-ui-redesign, branch worktree-soltui-ui-redesign, PR 85.

Completed: a read-only subagent inventoried soltui's functions and data surfaces without reporting layout. docs/design/soltui-v2/DESIGN.md lists 16 primary functions and groups them into five question-led destinations (Now, Signal, Research, Money, Library), with a health strip, a registry command palette and an Explain overlay. docs/design/soltui-v2/mockup.py is a standalone Textual 8.2.8 + textual-plotext app on fixture data; it imports nothing from soltui/. screens/ holds 7 SVGs rendered by `mockup.py --shots`. soltui/README.md points to the proposal.

Verification: headless render of all 7 screens at 160x48; pilot smoke run (5 destinations, rail selection, explain toggle, palette navigation); up/down palette passed the dataviz validator; scripts/check_docs.py passed; index/build.py all rebuilt the offline index and --check passed. No production code changed, so the 610 s soltui suite was not run locally; CI runs it.

Remaining: merge PR 85 (the background-job harness forbids this session from merging). Migration steps are listed in DESIGN.md section 11 and are not started.

## v119 - 2026-11-08 (SolTUI v2 implemented)

Target: prompts v63, Stele TASK-904, KNOW-916 (architecture), KNOW-918 (focus lesson). Worktree /Users/mitch/dev/solmargintrader/.claude/worktrees/soltui-ui-redesign, branch feat/soltui-v2-ui.

Backup: annotated tag soltui-ui-v1 and branch backup/soltui-ui-v1 at master 4d0f027 (classic 18-tab console), both pushed. `soltui --classic` shows the original tab bar in the new build.

Completed: soltui/shell.py (destinations, health strip, Needs-you, tiles, activity, signal hero, palette provider, Explain text, soltui-night theme) wired into soltui/tui.py. The classic #main-tabs TabbedContent keeps all 18 panes and ids; v2 hides its bar and drives it. New Now pane (tab-now). Keys 1-5, comma, [ ], ?, ctrl+p. main() opens on Now; SolTuiApp's default start stays tab-backtest for the suite. Unknown panes are filed under Research (with_extra_views). Help entries for tab-now and now-needs.

Verification: soltui/tests/test_v2_shell.py (14 tests: every pane reachable, extra pane filed, builders, keys, Explain, palette never runs a write, classic mode, --classic). Full soltui suite: 874 tests OK (2 skipped) in 766 s. Headless smoke against real state rendered Now with live data.

Remaining: deeper per-view interiors from the mockup (IQR strip in the Backtest leaderboard, diverging vote bars in the compound metric table) are not built. Open PR 87 (Bots v2) and tasks TASK-890 / TASK-873 also edit soltui/tui.py; expect merge conflicts in the CSS block and compose().

## v120 - 2026-11-08 (SolTUI v2 recovery)

Version: 120. Delta: v119 to v120; recover TASK-904 and PR93.

The owner asked Codex to resume the quota-exhausted Claude redesign. The accepted checkpoint is64662f0 on feat/soltui-v2-ui, with886 local tests passing (2 skips) and eight CI jobs successful. Backup tag soltui-ui-v1 and branch backup/soltui-ui-v1 remain at4d0f027. Preserve the five-destination shell, every classic pane, Explain, palette and --classic. Deeper mockup pane interiors were explicitly deferred in the accepted checkpoint.

Worktree: /Users/mitch/dev/solmargintrader-wt-01a1bb24. Tasks TASK-985 (recover/integrate), TASK-986 (verify), TASK-987 (deliver) block the original redesign task TASK-904. Current master8ed41ad contains substantial concurrent research/card work. Integrate all incoming changes and exact workflow history. The separate active card-catalog PR99 owns three pre-applied dirty canonical sources; do not touch them or any other shared-checkout files.

Remaining: resolve count/record/derived-index conflicts; verify merged-tree navigation and full TUI suite; preserve the prompt and recovery notes; push the final descendant to PR93, pass CI, merge and verify remote content; confirm installed launcher behavior without restarting existing consoles. No trading, inference or indexing services are authorized by this UI recovery.

## v121 - 2026-11-08 (SolTUI v2 narrow navigation repair)

Version: 121. Delta: v120 to v121; finish integration and repair the independent acceptance finding.

Integrated current master 8ed41ad in the private recovery branch and preserved all incoming workflow history. Fourteen focused shell tests, sixteen offline-index tests, documentation counts and offline index freshness passed before this correction. The full 898-case merged-tree local suite is running; its modules were loaded before the two new regression cases below.

Independent fresh-process acceptance on 36902a7 passed every classic pane (19 including Now), all Signal sections, keys, Explain, palette write safeguards, classic mode and input typing at 160x48. At 80/100 columns, the Research row clipped the active Indicators label. At 80 columns, the top bar also clipped the no-order-path badge. KNOW-990 records the exact trigger. The shell now uses a compact destination row with the safety badge and an active-view subnav with clickable previous/next controls when the full row does not fit. Two behavioral regression cases cover all selected Research views and badge visibility at 80, 100 and 160 columns. Classic pane interiors keep their existing sizing.

Remaining: rerun focused mounted acceptance and the 16-case shell suite, await the prior full local run, refresh offline indexes, pass final-head CI and merge PR93. Independent card-catalog PR99 remains owned by its original session. Preserve the canonical checkout and all unrelated work. Installed launcher acceptance and owned cleanup follow actual delivery.

## v122 - 2026-11-08 (SolTUI v2 final verification checkpoint)

Version: 122. Delta: v121 to v122; record the accepted narrow-terminal correction and delivery handoff.

All sixteen focused shell tests pass in 33.252 seconds. Independent mounted acceptance passes 88 selected-label checks across all 22 destination subviews while resizing 160 to 100 to 80 to 160 columns. Actual previous/next clicks wrap correctly at 80 and 100 columns; the no-order-path badge remains visible; 160 columns restores the full Research row. No mismatches remain in these checks. Classic pane interiors retain their existing sizing. The documentation gate now discovers 900 SolTUI tests and 2,195 cases across the documented suites. Offline-index regression cases and whitespace checks pass.

The full local merged-tree run began before the two new regression tests were added. It tests the prior 898-case tree; the focused 16-case run verifies the final shell delta. Final-head CI must run all 900 cases on the final source. The exact current delivery receipt, local suite result, final-head CI, merge commit and installed acceptance are maintained in Stele TASK-987 and /tmp/soltui-v2-resume-01a1bb24/checkpoint.json. Read those receipts before resuming any action below; do not repeat completed checks merely because this committed checkpoint predates the merge.

Remaining at this checkpoint: finish local full-suite observation, pass final-head CI, gated squash merge of PR93, verify actual remote source, safely synchronize the canonical launcher while preserving other sessions, and remove only the clean recovered redesign worktrees and branches. The backup tag and branch stay. No service restart, trading action, inference or semantic-index rebuild is part of this delivery.

## v123 - 2026-11-08 (SolTUI card catalog integration)

Version: 123. Delta: v122 to v123; preserve delivered PR99 before final redesign verification.

Concurrent strategy-card visibility PR99 merged as 3e5a9f3 while this task ran its checks. Integrated its source, existing-test corrections and full workflow history without changing card/registry behavior. The Research destination now names the view Strategies because it includes the active-card catalog and the curated roster. All 351 active cards, specification execution guards and registered-strategy controls remain intact. The five-destination shell still owns navigation.

Previous local full-suite and independent receipts qualify the pre-PR99 source, plus the separately tested narrow delta. Final combined-source CI is required. Repeat focused shell/catalog acceptance against this merged source, regenerate only offline retrieval artifacts, then finish PR93 delivery. TASK-987 and the private checkpoint hold the current delivery state. Preserve all other active work and do not repeat the card extraction, classification or installation workflow.

## v124 - 2026-11-08 (combined redesign accepted)

Version: 124. Delta: v123 to v124; record acceptance of the final combined source.

The combined sixteen-case shell suite passes in 28.124 seconds. Independent fresh mounted acceptance passes Now startup and Research to Strategies, with 351 active cards, 292 TradingView specifications and 34 registered strategies. Filtering and opening AveragePrice shows its equation. Specification Add, Backtest and Space stay blocked without roster or backtest writes. Registered-strategy controls and mocked backtest dispatch remain available. Strategies and the no-order-path badge remain visible at 80 and 100 columns. Source hashes and detailed observations are in /tmp/soltui-v2-resume-01a1bb24/acceptance/combined-catalog/receipt.json.

All source integration is complete. Documentation counts, whitespace and offline index freshness pass on the combined tree. Finish only the delivery gates tracked by TASK-987: observe the prior full local run, pass the complete 900-case final-head CI suite, merge PR93 at its verified final tip, confirm remote source, perform safe canonical synchronization and fresh launcher acceptance, then remove the clean owned worktrees and branches. TASK-987 and /tmp/soltui-v2-resume-01a1bb24/checkpoint.json are the authoritative final receipts; if they report completion, do not replay these steps. Preserve the classic backup and all unrelated active work.

## v125 - 2026-11-08 (local suite complete; final metadata aligned)

Version: 125. Delta: v124 to v125; finish local verification accounting and header consistency.

The full local pre-PR99 merged-tree run passed all 898 cases in 752.436 seconds with two optional skips and exit 0. The final combined source separately passes the sixteen-case shell suite, independent pane/navigation/input/classic acceptance and the merged 351-card catalog checks. The two new narrow-navigation cases bring final discovery to 900 SolTUI cases. Final-head CI remains the complete combined-tree gate. Verification task TASK-986 is complete; delivery task TASK-987 is active.

The workflow headers now agree with their latest entries: prompt version 63 and continuation version 118. All incoming history is preserved. No product source changed after the combined acceptance receipt. The current merge, CI, preservation and installed-launcher results are recorded in TASK-987 and /tmp/soltui-v2-resume-01a1bb24/checkpoint.json. Read them before repeating any remaining delivery action. The original clean Claude redesign worktree remains held by its live process and must be preserved; remove only the private recovery worktree after delivery.

## v126 - 2026-11-08 (delivered workbench integration)

Version: 126. Delta: v125 to v126; preserve concurrently delivered optimization workbench PR98.

Current master advanced to bc5c701 as PR98 merged. Integrated every incoming implementation, test, documentation and workflow record. Application hunks merged automatically. The experiment workbench remains on Research to Bots. Palette entries for experiments now navigate to Bots and focus the existing workbench button; experiment writes never dispatch directly. The palette safety test checks every experiment write command. Existing card catalog and the accepted shell remain intact.

Final discovery is 969 SolTUI tests and 2,264 documented cases. Previous receipts qualify their named earlier source. Final combined-head CI must include the 69 workbench cases plus the sixteen shell cases. Repeat focused shell and mounted workbench access after this merge. Final delivery remains TASK-987 and PR93. Preserve other active branches and shared work, the live locked original Claude worktree, and the classic UI backup.

## v127 - 2026-11-08 (CI accounting and remaining delivery)

Version: 127. Delta: v126 to v127; answer the owner's status question and record focused integration verification.

The owner asked whether CI is optional, whether this is the first run, and what remains. Explained that the repository shipping instructions require final-commit CI; only the informational Jupiter check is optional. Claude's original CI passed. Codex has started three further runs at this checkpoint. Two were superseded. One avoidable restart followed a record-header correction after CI began. The current 3607aea run was still running when PR98 advanced master and required integration.

The merged workbench source passes all sixteen focused shell tests in 26.477 seconds. The docs checker sees only committed test filenames, so its pre-merge-commit discovery still reports 900 while the disk contains the 69 incoming cases. Keep the correct final 969 count and rerun the checker after the merge commit. Do not rewrite the counts to the incomplete discovery result.

Remaining: finish independent workbench-entry acceptance, commit the combined source and complete final discovery/index checks before pushing, pass final-head CI, merge PR93, verify remote contents and the canonical launcher while preserving active work, and clean only the private recovery worktree. No extra UI feature is planned. TASK-987 and the private checkpoint retain live delivery receipts.

## v128 - 2026-11-08 (owner waives repeated full CI)

Version: 128. Delta: v127 to v128; apply the owner's current delivery instruction.

The owner instructed that another full CI run is unnecessary. This overrides the earlier standing requirement to repeat full CI for this delivery. Do not start or wait for another full suite. Preserve ordinary GitHub protections; never use an admin merge or force push. GitHub reports no master branch protection and no rulesets at this checkpoint.

Evidence remains precise: Claude's original full CI passed. Codex started three more runs; two were superseded rather than completed passes, and the third was still running at this checkpoint. The local 898-case run passed with two optional skips. The final combined workbench source passes all sixteen focused shell tests in 26.477 seconds. Independent mounted acceptance verifies the actual Bots workbench button, real schema and preview rendering, clean dismissal, every experiment write palette entry navigating without dispatch, preserved 351/292 card catalog, and 80/100-column navigation. No real optimizer job or service was started.

Commit this fully resolved integration with CI skipped, then verify final 969-case discovery/docs counts, offline index freshness and whitespace before pushing. Update PR93 with the exact verification scope and owner instruction, merge normally, verify the actual remote files, safely activate the canonical launcher under fresh preservation checks, and remove only the private recovery worktree. TASK-987 and /tmp/soltui-v2-resume-01a1bb24/checkpoint.json hold the final live receipts. Preserve the locked original Claude worktree and all unrelated active work.

## v129 - 2026-11-08 (EPIC-980 review checkpoint)

Version:129. Delta:v128 to v129; first cohort accepted and research runtime repair delivered.

TASK-981:18run-start frontier labels across4cohorts. Conditional3concepts/61structured+11auxiliary assertions passed72/72review; all original-group ledgers and exact-spans verified. Graph4concepts/96claims audited; one numeric quote repair preserves claim text, fresh gate running. Uncertainty4concepts/74claims drafted and under independent audit. Multiplicity7concepts researching.

TASK-982:14new concepts plus reused accepted grid coverage; all13user labels retained. First7bot concepts drafted154claims, authority/literal repairs underway; remaining7product/execution concepts researching. Full CFE re-expansion, canonical-bound private LCA/LDO packs, rollup and keyword indexing remain substantive work. Semantic embeddings stay paused.

Necessary parser repair TASK-994 delivered by llms-explorer PR310, merge97eb8e9e4bc978f822c2cf55a24d5af8c9773290. Both installed modules match merged bytes and reparse retained completed outputs; malformed tails still fail. Original divergent checkout and unrelated helpers preserved. Website staging now research/trading-publish-epic980.

Canonical private continuation v1.4.0: /Users/mitch/.global-ai-hub/research/trading-research-epic980/memory.md. No serial finish/publication yet; root owns combinedhub quality and all Git delivery. Remaining: complete audits/gates, guides/hub quality, substantive bot full-suite, serial publication, CI/merges and live acceptance. Do not duplicate active coordinator PID47913 or mutate shared original checkouts.
## v70 - 2026-11-08 (Forwardtest coins, auto-optimize, background runner)

Target: prompts.md Forwardtest coins entry. Branch feat/forwardtest-coins-optimize in /Users/mitch/dev/solmargintrader-wt-39e8bf11-fwd.

Completed: coin dropdown (one coin or All coins = every Coinbase USD market from `pricefeed.stream_products`); Auto-optimize on/off (`tick(tune=...)`); an adoption is saved as the trial's default (`forwardtest/defaults.json`, key coin|label|minutes) and seeds new trial rows (`_usable_default` refuses other members or unknown params); background runner thread on the Runtime (`forwardtest.run`, `forwardtest.state`), header shows it from every tab.

Measured: one check is 1.5 s per coin with 34 strategies x 4 horizons; a live two-coin run recorded 136 calls per coin and the thread exited on Stop.

Not reproduced: in-process, the old timer already kept ticking after a tab switch (pilot, 2026-11-08); the runner thread removes the UI from the loop either way.

## v111 - 2026-11-08

Target: PR 89, forwardtest coin selection and optimization. Stele TASK-998. Private worktree: /Users/mitch/dev/solmargintrader-wt-01a1bb38. Merging current origin/master into eecade5; preserve both workflow histories and regenerate indexes after conflicts are staged. Remaining: test, push, await final CI, merge and verify remote.

## v112 - 2026-11-08

TASK-1001: PR 89 final CI at 0d2ba8d passed; SolTUI took 15m35s, all other jobs at most 1m13s. Master advanced to bc5c701, so merge again. Inspect test timing and implement conservative change-aware checks and parallel full coverage; preserve scheduled/manual full coverage. Stele decision outbox 03002488. Remaining: implementation, tests, fresh CI, PR merge and delivery. Worktree: /Users/mitch/dev/solmargintrader-wt-01a1bb38.

## v129 - 2026-11-08: CI latency and PR 89 integration

PR 89 SolTUI CI ran 895 tests in 893.969 seconds and logged 165 app mounts. Other jobs took at most 73 seconds. Added conservative test-only module selection, four timed shards and nightly full coverage. Merged master through 9bd7067; combined discovery is 980 tests. Remaining: run focused integration, regenerate indexes, push and verify final CI, then merge PR 89. Stele outbox 03002488.

## v130 - Coin suitability implementation

The user requested a reusable skill/CLI for one or many coins, then added quick heuristic and detailed audit backtests plus a Bots-tab rank/sort button. Canonical implementation belongs here so all surfaces reuse the existing grid/DCA economics. The earlier independent stdlib prototype in the research worktree is archived, not installed or advertised as production code.

Worktree: /Users/mitch/dev/solmargintrader-coin-fit-20261108, branch feat/bot-coin-fit, base8ed41ad. Preserve the maintained checkout's unrelated minute_coverage edit and untracked web application files. No signing, order, executor or live configuration changes. Backtest code remains offline.

Reuse backtester.core.gridsim and dcasim for next-bar, pessimistic, fee-aware simulation. Quick ranking uses an older development window and reserves the newest holdout. Audit runs the fixed configuration over chronological windows, a continuous full-capital path, and stressed fees/slippage; it does not auto-adopt a configuration or claim independent profitability from a ranked winner. Current-cache membership is not a historical universe. Missing live depth, fundamentals and portfolio stress remain explicit in the22-field template.

Parent owns soltui/coin_fit.py, backtest computations, CLI/skill, tests/docs/workflow/Git. Textual lifecycle specialist owns tui.py, commands.py, help.py, optional bots_screens.py and dedicated UI tests. Backend interface: rank_coins(bot,coins,settings,mode,start,days,progress,cancelled). Frozen input/config, bounded windows, cooperative cancellation, deterministic rows including errors. The small Stele reader model was unavailable; direct recall found KNOW-871 (train-rank caution), KNOW-531 (no orders/keys), TASK-870 (superseded Bots implementation). No unrelated project binding is created.

Remaining: backend+CLI/skill, UI, synthetic invariants/no-lookahead tests, audit and live cached-data smoke, installed UI acceptance, full required checks and merged delivery.

## v131 - Verification checkpoint

Implemented the shared offline coin-fit backend, direct/skill script entrypoints,22-field evidence output, deterministic single/bulk ranking, quick development-only scoring and10audit scenarios. Existing grid/DCA economics remain unchanged. Scheduled accumulation uses a separate explicit prefunded next-open schedule. The TUI freezes config, capital, policy, dates, costs and input hash; its selected audit preserves the quick order. Threaded jobs support cancellation, stale/context guards and teardown. No live order or config adoption exists.

Independent forward review hand-reconciled60grid/DCA scenarios and a scheduled-account example. It found and rechecked fixes for explicit-cache fallback, inaccurate audit as-of, minute alignment, malformed context, missing context identity, hidden failed UI checks and incomplete cost/inventory/ledger display. No residual findings from that review.25new economic/screener tests plus13new UI tests pass; focused registry/help/bridge checks pass. Full backtester run909cases has only expected lexical-index staleness while uncommitted; full SolTUI run is active. No archived study is represented as a current profitability proof.

Next: commit tracked source so deterministic index/test counts can refresh; run full checks and CI, then merge. Install the skill by symlink to the maintained checkout after delivery. Verify actual installed TUI entrypoint and click flow. Keep the maintained checkout's dirty files untouched. Context recall small-model agent could not run; direct MCP recall was read-only and no project binding was created.

## v132 - Concurrent catalog integration

Merged source master3e5a9f3(PR99) with the coin-fit feature. Both Strategies catalog behavior and Bots ranking survive. Preserved incoming logs verbatim; own unpublished sections now111/112 and prompt61. Help tables combine both contexts; button registry has70handlers(67incoming plus3coin-fit). Rebuild only offline retrieval indexes after final tracked source changes.

## v133 - Reviewed feature and verification gates

The independent review rechecked all findings and reports no residual issues. Economic tests hand-check next-open, full-capital and terminal-cost accounting. Quick scoring ignores the reserved newest window; audit refuses changed data and preserves frozen config/costs/capital/policy. All22 template fields distinguish simulation evidence from unknown current depth and eligibility. Scheduled accumulation needs a supplied ownership thesis for a positive screen. Source and methodology documentation are complete; skill validation passes.

Thirty-eight focused economic/screener/UI tests pass, plus registry/help/bridge coverage. The first909-case backtester run found only expected offline-index staleness before metadata refresh. Full SolTUI validation and final CI are required on the integrated head. Only offline metadata/text/concept indexes are regenerated; no embeddings, service restarts or live operations are part of this feature. Actual installed-entrypoint acceptance will distinguish a fresh guarded session from the owner's older Terminal TUI PID.

Candidate branchfeat/bot-coin-fit remains recoverable; finish final-head gates, merge, safe canonical fast-forward, installed skill symlink and actual installed click flow. Preserve unrelated source and current consoles. Final Git/install/cleanup identities will be stored in a private receipt outside tracked source to avoid a post-merge bookkeeping commit loop.

## v134 - coin-fit final local verification

Backtester909 tests pass after the offline index refresh. Full SolTUI913 ran with one failure: test_every_table_has_a_title_above_it reported bots-fit-table. An explicit table title fixes that failure; the affected title and coin-fit UI suites pass14 tests. Final CI must verify the complete integrated head. Two new test import-order findings were fixed; scoped Ruff passes. No existing unrelated UI lint is claimed clean.

Cached23-coin quick smoke retained11 complete and12 insufficient-data rows without bridging missing candles. A separate SOL/BTC/ETH audit exercised all three supported bot types and ten scenarios each. These are operation checks, not an investment recommendation or calibrated edge. PR: https://github.com/mithudso/solmargintrader/pull/102 . Final merge/install acceptance remains pending; the final private receipt will be /Users/mitch/dev/crypto-grid-dca-research/evidence/coin-fit-final-delivery.json . Existing native consoles, WIP and paused services must remain preserved.

## v135 - Workbench integration

Merged published optimization workbench PR98 at bc5c701 into the coin-fit branch. Preserve its experiment lifecycle, sealed holdout safeguards and Strategies browser. Both new and existing Bots controls remain. Combined suite discovery is expected to be982SolTUI and909backtester; final checks verify actual counts. No live configuration, service or order changes.

## v136 - v2 shell integration

Concurrent PR93 published the v2 shell at9bd7067. Preserve Research→Bots and the classic Bots tab. Production source auto-merged; a regression exercises actual Rank/Audit clicks in both full shells. Recompute combined discovery and offline metadata. Final CI and installed acceptance remain the delivery gate for this feature; prior research and other owners' verification outcomes are historical scope, not proof of this combined revision.

## v137 - Optional full SolTUI suite

The owner explicitly requested: make the999-case SolTUI suite optional, skip it and push the code. Cancelled the running full-suite job. CI now runs it only for workflow_dispatch with run_soltui_suite=true; normal PR/push jobs skip it. Keep the existing check name stable. Other fast CI checks remain enabled. No full999-case pass is claimed. Local909backtester checks, focused36-case combined v2/classic UI checks and independent accounting/source preflight passed; installed-primary acceptance remains after merge.

## v138 - Forwardtest and optional CI integration

Concurrent PR89 published forwardtest control changes and conservative timed CI shards atfedde2a. Preserve those functions and scripts. The owner's newer explicit optional-suite instruction controls the full SolTUI job: only workflow_dispatch with run_soltui_suite=true enables all four shards. PR, push and scheduled workflows skip this job; other jobs stay enabled. Combined discovery is1010cases after incoming11additional tests and this feature30tests. No full suite is run or claimed passed.

## v139 - 2026-11-08 (canonical UI activation)

Version: 139. Delta: v138 to v139; recover the actual launcher after the owner merged PR93.

The owner merged PR93 as 9bd7067d30af3a3fad93120d989d8fa409834966 from source 4e4693e. All 27 task paths match the actual merged commit, which is present on remote master. The owner waived repeated full CI; obsolete run 42482448847 was cancelled. The ordinary merge guard had refused the automated merge during its two-minute new-push check-registration window; the owner then merged it.

The launcher still delegates to canonical checkout 3e5a9f3. A normal fast-forward safely refused to overwrite another live session's changes in soltui/commands.py, soltui/help.py and soltui/tui.py. These are guide/card behavior changes and must be preserved. The owner explicitly reports that new console launches still show the old UI. TASK-1002 owns actual activation and blocks final delivery TASK-987.

The guarded runtime writer prepares a private three-way merge against canonical base 3e5a9f3 and merged source 9bd7067. Only the nine required runtime Python files are eligible: bots.py, commands.py, experiment_jobs.py, experiment_runner.py, experiment_screens.py, experiments.py, help.py, shell.py and tui.py under soltui. The writer backs up preimages, verifies fresh hashes and installs atomically. It does not change shared Git HEAD/index/branch, stash work, edit other dirty files or restart services. Independent fresh launcher acceptance follows installation. The canonical runtime will be qualified by installed hashes plus retained local changes, not described as a clean Git revision.

Stele transport closed after TASK-1002 creation and claim. Exact writes are queued in outbox IDs 20e78a8c, 608187fb and 3f944787. Installation, preservation and rollback receipts belong under /tmp/soltui-v2-resume-01a1bb24/activation/. Remaining: finish guarded installation, verify actual new launches open Now while retaining local guide behavior, record final hashes and receipts, ship only this follow-up workflow record without another full CI, and clean only the private recovery worktree. Preserve the locked original Claude worktree and all other active work.

## v140 - 2026-11-08 (actual runtime installed)

Version: 140. Delta: v139 to v140; qualify the installed canonical runtime by exact source hashes.

The guarded writer installed all nine runtime files from merged source 9bd7067. It retained the active guide/card changes in commands.py, help.py and tui.py through clean three-way merges. It checked 1,036 unrelated existing dirty/untracked paths and found no changed bytes during installation. Canonical Git HEAD remains 3e5a9f3 and index bytes remain unchanged. The first preflight detected an index-byte change and refused before writing; a fresh preparation qualified the stable state before installation. Publication used fresh hash preconditions and atomic file renames; it does not claim a true compare-and-swap against arbitrary concurrent writers.

Actual canonical imports pass. The normal /Users/mitch/.local/bin/soltui wrapper now exposes --classic in --help. The actual main entry point, with only run stubbed to prevent service startup, constructs tab-now with v2 enabled; --classic constructs tab-backtest with v2 disabled. The installed registry has 106 commands. Existing guide-only filtering and wording remain intact. No service, real optimizer job or trading action was started.

Install receipt: /tmp/soltui-v2-resume-01a1bb24/activation/install-receipt.json. Backups: activation/before/. Import and entry-point proof: activation/canonical-import.json and launcher-help.txt. Guarded rollback helper: activation/rollback_runtime.py (not run). TASK-1003 is the install subtask; TASK-1002 owns final independent canonical acceptance. These are runtime overlays, not a clean checkout of the merged SHA. A future synchronization must preserve the installed redesign and the user's concurrent guide edits; never overwrite the hybrid runtime with an older branch's UI files.

Final independent mounted acceptance is saved under /tmp/soltui-v2-resume-01a1bb24/acceptance/canonical/. TASK-987 and the private checkpoint hold the current final result and any remaining work. Read those receipts before repeating installation or tests. Ship this workflow-only follow-up without another full CI run under the owner's explicit instruction. Preserve the live locked original Claude worktree and every other active task.

## v141 - 2026-11-08 (canonical acceptance and final records)

Version: 141. Delta: v140 to v141; finish actual loaded-UI verification and retain incoming PR89.

Independent canonical acceptance passed with process exit 0. The actual normal wrapper exposes --classic. Fresh canonical mounts verify Now startup, soltui-night theme, five destinations, Explain, Bots workbench, classic fallback, write-safe experiment navigation and 80/100-column labels. Current guide behavior remains intact: 34 registered cards, zero TradingView cards, 42 guide files excluded, and nonregistered guide keys refused. All nine installed runtime hashes match before and after verification. Canonical HEAD 3e5a9f3 and index bytes remain unchanged. Existing consoles were not restarted.

Final acceptance is /tmp/soltui-v2-resume-01a1bb24/acceptance/canonical/receipt.json. TASK-1002 is complete; installation subtask TASK-1003 is complete. Three queued writes from v139 were replayed and marked done, and gap KNOW-1004 auto-archived when activation completed. The actual new-launch behavior is fixed.

While the workflow-only follow-up PR103 was open, PR89 merged as fedde2a. Preserve its forwardtest implementation, conservative CI scope/shards, every prompt/memory entry and current documentation counts. This follow-up changes no product source. Restore only the missing closing fence on this task's existing CI-waiver prompt; preserve the owner's exact text and all incoming history. Regenerate offline retrieval artifacts, check final documentation/index/whitespace, push this record-only integration with CI skipped, finish ordinary PR103 merge and verify its exact content, then remove only the clean private recovery worktree. TASK-987 and the private checkpoint hold final delivery closure; do not replay installation or full tests.

## v142 - 2026-11-08 (activation record integration)

Version: 142. Delta: v141 to v142; preserve incoming coin-suitability and scoped-CI delivery.

Concurrent PR102 advanced master to 078c895 while the workflow-only PR103 awaited merge. Preserve all incoming source, tests, CI policy and exact workflow history. This follow-up still changes only prompt/continuation records and offline retrieval indexes. Canonical UI activation remains independently accepted under its installed hashes. No runtime reinstall or full test suite is required for these record-only merges. Complete the ordinary PR103 merge, verify exact five-artifact content, and clean only the private worktree.


## v143 - 2026-11-08 (guide and strategy separation)

Version: 143. Delta: v142 to v143; user supersedes the earlier policy that allowed indicator-only specifications in the active strategy folder. Preserve content and move guides to a guides directory and other untestable material outside the active strategy folder. The loader reads only flat cards; 312 of 351 lack runners. Verify actual strategy capability, coverage manifests, UI, and paths; do not infer that all missing-data runners lack implementations. Task TASK-992; worktree /Users/mitch/dev/solmargintrader-wt-guides, branch feat/strategy-guides. Preserve concurrent sessions. Remaining: classify each card, move content, adapt coverage, validate, deliver, and safely synchronize canonical checkout.


## v144 - 2026-11-08 (immediate canonical correction)

Version: 144. Delta: v143 to v144; the owner corrected the failure to move cards. Move the verified no-runner active cards immediately in both the private worktree and canonical checkout under byte and collision checks. Put identified educational guides in backtester/guides and other non-runnable cards in backtester/strategy_research. Then update evidence paths, coverage, tests, UI wording, and finish delivery without touching concurrent work. TASK-992 and draft PR101 remain active.


## v145 - 2026-11-08 (SolTUI list requirement)

Version: 145. Delta: v144 to v145; owner explicitly requires SolTUI list to reflect the moves. The nonrecursive active loader automatically excludes the312 pre-applied moves, but update misleading status labels and verify fresh mounted SolTUI. Six identified guides and306 other no-runner cards have been moved in both canonical and private worktree under verified byte preconditions; receipt /tmp/strategy-guide-moves-992.json. Coverage paths and hashes must be updated before completion. Audit remaining incomplete guides.


## v146 - 2026-11-08 (owner corrected remaining templates)

Version: 146. Delta: v145 to v146; owner explicitly classified JLP/SOL, BTC/ETH pair cards and resting-ladder grid as non-strategy guides/templates. Move these and the two other unregistered bot templates out of the active strategy directory. Registered strategies remain subject to registry and implementation tests. Retain separate simulator code and keep documentation contract tests bound to the relocated files. SolTUI must list only registered strategies.


## v147 - 2026-11-08 (canonical moves and SolTUI verified)

Version: 147. Delta: v146 to v147; moved 348 files byte-for-byte in canonical and private worktrees under exact preconditions. The active catalog now has34 registered strategies;42 guides and templates,306 other research cards, and760 incomplete cards preserve all1142 documents. The named JLP/SOL, BTC/ETH and resting-ladder examples and two other unregistered bot templates are in backtester/guides. Coverage manifest and checker follow all four locations; canonical coverage passes. Relocated simulator card drift checks remain enabled. SolTUI filters to registered strategy cards; focused63 tests pass and lint is clean. Canonical runtime and checker paths were pre-applied under hash receipts /tmp/strategy-guide-ui-992.json and /tmp/strategy-guide-checker-992.json; moved-file receipts /tmp/strategy-guide-moves-992.json, /tmp/strategy-guide-more-992.json and /tmp/strategy-template-moves-992.json. Final fresh SolTUI acceptance, offline index refresh, final-head CI, merge and safe canonical reconciliation remain. No research card bytes changed.


## v148 - 2026-11-08 (concurrent upstream integration)

Version: 148. Delta: v147 to v148; owner asked whether all newly created cards were moved. Verified all1083 extracted cards are outside the active folder. The canonical checkout has34 registered active,42 guides/templates,306 research and760 incomplete. PR101 is integrating four upstream commits; preserve their v2 UI, forwardtest, workbench and bots changes. Fresh canonical mounted acceptance previously passed. Finish conflict resolution, update generated indexes, validate the merged v2 UI, push, check and merge without overwriting other work.

## v139 - 2026-11-08: targeted SolTUI gate

PR 89 merged as fedde2a while CI ran. PR 102 made the full suite manual-only at the owner request. Add a bounded changed-area gate for PRs and pushes with bridge smoke and explicit mappings; unknown paths keep smoke. Full sharded coverage stays opt-in. TASK-1001 tracks final validation and delivery.

## v143 - 2026-11-08: PR 104 conflict resolution

PR 104 passed targeted CI at 609882b, but PR 103 advanced master to 15b9a2e. Preserve both continuation histories and regenerate offline indexes. Remaining: push resolution, check final CI and merge. TASK-1001 tracks delivery.

## v144 - 2026-11-08: second PR 104 integration

PR 100 advanced master to 98b92c1 after PR 104 final checks passed. Preserve its research and continuation records, regenerate indexes, then verify and merge PR 104. TASK-1001 remains active.

## v145 - 2026-11-08: PR 104 and PR 101 integration

PR 101 advanced master to 69140b8. Preserve guide separation and both continuation histories. Regenerate the indexes, verify and merge PR 104. TASK-1001 remains active.

## v139 - 2026-11-08

Active: Stele TASK-1006. Worktree: /Users/mitch/dev/solmargintrader-wt-01a1bb5b, branch agent-01a1bb5b, base origin/master 078c895. The original checkout is dirty and other sessions are editing SolTUI; preserve their work. Goal: show selected strategy card and coin details in shared editor and stream backtest logs there. Backtest lifecycle specialist is examining separate job sources. Remaining: implement selection and logs, test, integrate current remote, deliver and verify live installation.

## v140 - 2026-11-08

TASK-1006: registered and roster strategy selection opens the full card; selected coin previews its overview; queue backtests follow a bounded worker log; CPCV progress and Compound/Bots engine callbacks populate the editor. Unsaved file edits are protected and later navigation is not stolen by log updates. Focused tests: 29 passed in test_tui backtest/strategy cases, test_backtest_log, test_bgworker, and test_editor_backtest. Broader relevant regressions running. Remaining: integrate latest origin/master, verify checks and remote delivery, and verify actual loaded app without disrupting concurrent sessions. The original checkout is dirty and shared; never reset or switch it.

## v146 - 2026-11-08: PR 96 conflict resolution

Owner confirmed the existing merge was abandoned. Preserve its staged merge against 2d9e27b, merge the native-card source reviews with the newer catalog relocation, verify source profiles and card integrity, run CI, and merge PR 96. The offline catalog, native-profile and full-script gates pass after updating links for relocated cards. Source profile hashes and independent review bindings remain intact. Remaining: final checks, commit, push and verify merge.
## v146 - 2026-11-08

Integrated upstream guide separation and targeted CI. After catalog integration, four editor/strategy tests passed; earlier 27 focused tests passed. Compound and v2 shell regression cases passed, but the combined invocation also named nonexistent soltui.tests.test_commands and therefore exited 1 (90 actual tests passed plus one import error). Current live process PID 50024 loaded before these changes from the dirty shared checkout; loaded bytes are unverified and it cannot auto-reload. Leave that checkout and process alone. Remaining: final PR checks, merge, remote content verification, and a safe new-launch acceptance test.

## v147 - 2026-11-08

PR 105 was merged externally as 2d9e27b while its CI was still running. The docs check reported stale test counts caused by five added tests. PR 106 corrects counts to 1015 SolTUI and 2319 total; scripts/check_docs.py passes locally. PR 106 also scrolls the log to the latest lines. Browser e2e failure from PR 105 awaits CI logs. Live process remains on the shared dirty checkout and has not loaded these changes.

## v149 - 2026-11-08

Target: resolve SOL background sweep proof mismatch; Stele TASK-1009. Worktree: /Users/mitch/dev/solmargintrader-wt-01a1bb71. Preserve the shared checkout and active processes.

Diagnosis: persisted SOL proof differs from current code in 26 Python paths and from both current SOL candle files; settings match. Existing results and proof remain untouched. Queue uses the default results file; the CLI fresh-path workaround is not visible in Queue. A fresh sweep must not merge old and new evidence.

Verification: the live checkout fresh-path --plan succeeded with 1,059 pending jobs and did not run evaluations. The running TUI still reads the old default history.

Remaining: implement safe Queue recovery with archive and lock semantics, verify with isolated data, deliver the code, and verify loaded behavior without disrupting the active session. No new sweep was started.

## v150 - 2026-11-08

TASK-1009 resumed in /Users/mitch/dev/solmargintrader-wt-01a1bb7d. Existing history and its proof must remain paired and incompatible results must not mix. Current SOL candle and code hashes differ from saved proof; the rejection is valid. The Queue reads the default path and cannot use the CLI fresh-path workaround. Implement and test safe recovery, deliver, and verify actual loaded behavior without disturbing the active TUI or other services.

## v151 - 2026-11-08

TASK-1009: Queue Start fresh reserves a separate history under the worker lock and atomically selects it; normal Start resumes that history. Queue and strategy views follow the selection and retain proof isolation. 151 focused tests passed (one skipped), and the dedicated UI button test passed. A broader UI run was interrupted after NoMatches: #btn-add and is not claimed as passed. Remaining: update documentation counts, final CI and delivery; verify installed fresh-launch behavior while preserving the active process and historical results.

## v150 - 2026-11-08: liquidity archival

Target: liquidity, Aero LP, positions and liquidity scout. Stele task TASK-1011. Owner describes these as unprofitable. The live Aero LP launch agent was disabled and unloaded and /Users/mitch/.aero-lp/KILL was set. The standalone GitHub repository mithudso/aero-liquidity was archived. The managed exit-to-safe dry run reports no managed positions. The existing status snapshot reports no positions; a live unstaked NFT scan found none but cannot exclude gauge-staked positions. Preserve wallet data and records. User clarification is pending on whether to withdraw any remaining on-chain positions. The archive notice is recorded in the component documentation and overrides older live-operation guidance. The draft delivery is PR 108. Remaining: settle navigation handling and whether any independently staked positions should be withdrawn, then verify and deliver. Worktree: /Users/mitch/dev/solmargintrader-archive-liquidity.

## v151 - 2026-11-08

Owner confirmed Archive navigation and withdrawal of any remaining Aero LP positions to the wallet. Archive navigation is implemented in the isolated worktree. CDP history found three known Aero NFTs; each was burned on 2026-11-06, and Base RPC found zero manager balance and no stake in the known gauge. No withdrawal was needed or sent. This does not rule out all third-party staking paths. Keep the daemon disabled and KILL set. Verify navigation, finish PR 108, and verify delivery.

## v154 - 2026-11-08

Task: Fix Signal Call and Metrics edit error, Stele TASK-1018. Worktree: /Users/mitch/dev/solmargintrader-wt-metric-weekend; base origin/master 788d5a8. Sorting changes the displayed row order, but Apply and Toggle used the original component order. The editor correctly follows the displayed row key, so gate_session weekend could be sent to vwap_side. Updated both actions to use displayed row keys. The sorted edit and toggle regression passes in a Textual test with temporary settings. Eight Compound tab and click tests pass. Remaining: verify loaded app and deliver.

## v155 - 2026-11-08

Task: Signal Backtest reports bad value(s) in fds_to_keep (Stele TASK-1021). Worktree /Users/mitch/dev/solmargintrader-wt-backtest-fds, based on origin/master 788d5a8. Compound all-coins and frontier use ProcessPoolExecutor in a background thread. Textual stderr capture returns -1 from fileno; multiprocessing resource_tracker passes it into spawn and fails with bad value(s) in fds_to_keep. Wrapped the capture to raise UnsupportedOperation when no fd exists, while preserving writes. A fresh-interpreter Textual test starts real child workers; the same test fails with the unwrapped capture and passes with the fix. Preserve live processes and data. Remaining: integrate with the concurrent metric fix, rerun checks, deliver, and restart the interactive console only when safe.

## v156 - 2026-11-08

TASK-1009: The current interactive SolTUI process started after PR 109 and uses the current checkout. Its Sweep pane shows the saved error in /Users/mitch/.config/soltui/bg/state.json from a stopped worker at 09:07. Existing results and proof remain unchanged. The Start fresh button creates a separate history only when selected; opening the tab must not start a worker. Update the display to identify the prior error and explain that Start fresh preserves history. The status now labels the prior proof error and points to Start fresh. All 82 queue and fresh-history tests pass. Remaining: index refresh, CI and delivery; verify live process acceptance without disturbing the user session.

## v157 - 2026-11-08

The active SOL sweep uses a new proof-bound results file; 1d jobs succeed and 1h jobs fail. The Coinbase SOL_1h.csv contains three six-hour jumps, with 15 missing bars total. Direct Coinbase reads confirm all 15 remain unavailable. Binance.US returns bars at each missing hour, but its venue prices must not be silently mixed with Coinbase. Do not modify the active data or proof while its worker runs. Preserve historic results. User was asked whether to use a recent continuous range or investigate other sources. Stele task create queued in outbox 33ab8890 because transport closed. Remaining: determine a complete honest source or chosen range, verify, preserve worker and proof, and deliver. Worktree: /Users/mitch/dev/solmargintrader-wt-hourly-gaps.

## v158 - 2026-11-08

Owner authorized synthetic bars for the proof of concept. Three gaps contain 15 missing hourly bars in total. Stopped prior worker at its job boundary. Original price cache and prior results remain untouched. Created separate /Users/mitch/.config/soltui/poc-data/sol-hourly-synthetic-epsmf8t9 with original copy, a 15-bar flat previous-close zero-volume hourly series and SOL_1h.synthetic.json provenance. New worker PID 26985 uses that directory and writes separate results /Users/mitch/.config/soltui/bg/results-8f615318bd7af7168ba68c0469d43b7c.jsonl. These outputs use synthetic data and are not real-market evidence. CLI overrides data-dir for this run; ordinary UI Start does not retain that override and will refuse proof mismatch rather than mix data. Verification: multiple 1h jobs finished successfully in the running worker. Remaining: deliver records and retain the worker and historical files.

## v159 - 2026-11-08

TASK-1024 in /Users/mitch/dev/solmargintrader-wt-archived-alerts: user reports archived Aero LP kill alert on the home page. The needs list, health strip and Aero LP tile still project liquidity.status after archival. Remove those home projections and their polling, retain Archive and KILL safety state, verify other alerts and mounted UI, and deliver.

## v160 - 2026-11-08

TASK-1024: removed archived LP from home needs, health, tiles, and recurring home polling; Archive remains accessible and KILL is unchanged. Isolated home regression and mounted startup passed 11 tests. A broader UI run using the live configuration failed with NoMatches for #queue-status; no broader pass is claimed. Remaining: final verification, index refresh, CI, delivery and loaded launcher acceptance.

## v161 - 2026-11-08

TASK-1024: a delayed Queue activation during palette teardown raised NoMatches for #queue-status. The activation now checks that the widget exists. All 17 isolated v2 shell tests pass, including the formerly failing palette test. The independent mounted check verified archived LP suppression and other alerts. Remaining: rebuild indexes, final CI, merge and normal-launch acceptance.

## v162 - 2026-11-08

Active: Stele TASK-1027; branch agent-01a1bc24, worktree /Users/mitch/dev/solmargintrader-wt-01a1bc24. Owner requests separate 1, 5 and 30 minute forward predictions and results, and clear coin coverage. The Compound Signal forward test currently records only five-minute calls; it uses a distinct pipeline from the separate Forwardtest tab, which is being changed by another session under TASK-890. Preserve historical records and avoid presenting a five-minute candle as a one-minute result. Need causal minute data, separate horizon evidence and honest running-coin status, tests, live verification, and delivery.

## v163 - 2026-11-08

In /Users/mitch/dev/solmargintrader-wt-01a1bc24, added separate forward records and settlement for 1, 5 and 30 minute horizons using future one-minute opens and closes. All three evaluate the same five-minute Signal forecast; the code does not generate new forecasts every minute or train separate horizon-specific models. Missing candle data stays pending, old five-minute records remain intact. The Signal screen shows horizon counts, calls, outcomes and coin coverage. At inspection process 74947 in /Users/mitch/dev/solmargintrader held trainer locks for BTC, ETH, SOL, XRP, HYPE, DOGE, LINK, NEAR, SUI and AVAX; their logs showed recent checks. That old process does not load the new code. Focused forward tests: 12 pass; full soltui.tests.test_compound: 77 pass; scripts/check_docs.py passes after count updates. Remaining: review exact diff, deliver with CI, preserve other active worktrees and existing trainer, then verify the loaded app and running trainer on the delivered revision.

## v164 - 2026-11-08

Owner also reports a stopped SOL sweep because the evaluation proof is missing or differs for /Users/mitch/.config/soltui/bg/results-8f615318bd7af7168ba68c0469d43b7c.jsonl. Preserve the existing history, diagnose the actual proof mismatch, and continue in isolated compatible evidence rather than accepting unproven old results. The textual-job-lifecycle-specialist owns sweep implementation and tests in this worktree; do not overwrite its changes. The Signal horizon branch now samples the latest closed-five-minute forecast separately on 1-, 5- and 30-minute cadences; it does not train independent horizon-specific models. Focused horizon and runner tests pass. PR 115 is a draft pending CI and live acceptance. The current console and trainer both run old code from the shared main checkout; do not claim the changes are active.

## v165 - 2026-11-08

Sweep recovery TASK-1029 implemented by textual-job-lifecycle-specialist in branch agent-01a1bc24-sweep. The affected SOL proof bound its hourly input to /Users/mitch/.config/soltui/poc-data/sol-hourly-synthetic-epsmf8t9/SOL_1h.csv; current data path differs. On a selected UI sweep proof mismatch, reserve and select a separate fresh results segment while holding the worker lock, persist provenance and a synthetic-input notice, and retain the old history and proof unchanged. Explicit CLI paths still fail closed. Strategy cards now enter the evaluation fingerprint. Focused specialist tests: 152 passed, one skipped; reproduction used a temporary copy of the actual 1,059-row file and proof with a mocked evaluation, leaving both byte-identical. The Signal in-app Auto-forward timer also samples each minute and records horizon calls even when the five-minute source bar is unchanged. Focused Signal ledger/cadence and runner checks pass. Remaining: deliver both PRs, verify actual loaded app/trainer and safe recovery of the live sweep without mixing proof contexts.

## v166 - 2026-11-08

The SOL sweep resumed in a new proof-isolated results segment /Users/mitch/.config/soltui/bg/results-b97fdfd3748763c996ba74a0ddb12fde.jsonl. The old results and proof remain in place. As of 17:38 UTC it had completed 554 of 1,059 evaluations without an error; process 83636 runs from /Users/mitch/dev/solmargintrader-wt-01a1bc24, whose data symlink points to the original checkout. The ten-coin Signal trainer was gracefully replaced with PID 91333 from the same worktree. Each coin has separate 1-, 5- and 30-minute prediction records; initial one-minute outcomes resolved for BTC and SOL. The console PID 74766 still uses /Users/mitch/dev/solmargintrader and has not loaded the updated UI. Computer-use access to Terminal was denied. The active autopilot still points to the original checkout, so a future automatic restart can reload its older code until that checkout is safely updated. Preserve the active worktree and processes. PR 117 delivery and the five- and thirty-minute live outcomes remain to verify.

## v167 - 2026-11-08

Active: Stele TASK-1034. Worktree /Users/mitch/dev/solmargintrader-wt-status-1034, branch agent-status-1034 based on origin/master 4c4a4e7. Request: status button on every test tab, reopen the correct operation in the editor after navigation, show existing operation state and logs without starting or interrupting jobs. Stele decision write queued in outbox 2012e44c. Inventory test surfaces and their status/log sources, implement independent per-operation logs and reconnection, test missing logs, navigation and concurrent jobs; deliver after coordination with parent session. Parent owns separate paper experiment feature and active sweep worktree.

## v168 - 2026-11-08

The v2 Dry Run tab was passing a strategy string to extension/tools/dryrun.js, but that script ignores it and always simulates the grid. Removing the false strategy association, /Users/mitch/dev/solmargintrader-wt-status-1034 now routes registered strategies and selected Top 5 configurations to independent historical simulations using the existing backtest engine and cached candles. It labels the run as historical, not prospective, and keeps no order path. Adds a neutral baseline and strategy picker, Start dry run, progress logs, and test-status buttons. Test status retains separate simultaneous logs and reopens editor previews. Stele new task create queued in outbox 03b25b07. Remaining: full focused UI tests, resolve any failures, run documentation gate, commit and coordinate integration with parent; do not disturb active jobs.

## v169 - 2026-11-08

Implemented 10 test-status buttons with independent in-session operation logs, bounded detached-worker log retrieval, responsive status refresh, and unsaved-editor protection. Dry Run now runs the exact selected registry strategy or Top 5 composite on cached historical bars with the shared simulation engine. It does not run Node grid code, claim a profitable recommendation, use live prices, or place orders. Verified 36 bridge parity/surface tests, 39 preset/editor/handler tests, the 25-test initial UI subset, and targeted tests for narrow layout, actual selected strategy and detached log boundaries. Two additional focused UI tests passed after the thread-safe callback refactor. Stele TASK-1034 remains in progress; new Dry Run task and decision are queued in outbox IDs 03b25b07 and 2012e44c. Remaining: commit, update suite counts, push draft, coordinate parent integration and verify loaded app; preserve active trainer and sweep.

## v170 - 2026-11-08

Actual cached-data smoke on the status branch initially failed because SOL_1h.csv has gaps. The Dry Run now selects only the latest contiguous real candle segment and reports its exact dates and excluded bar count. A historical RSI run on /Users/mitch/dev/solmargintrader/data/SOL_1h.csv completed using 4,410 of 24,999 bars, excluded 20,589, and recorded 78 simulated fills. No prices were fabricated and no orders were placed. This is a historical smoke, not proof of live behavior or profitable future performance. Focused gap regression passes; draft PR 118 awaits integrated tests and coordinated delivery.

## v171 - 2026-11-08

PR 118 CI at head 26d4ec5 reported the backtester and docs checks failed because the committed offline retrieval indexes were stale after source, test and documentation changes. Rebuilt the three tracked offline indexes with index/build.py all. The builder does not run embeddings or contact the network. The exact failing backtester index staleness test and scripts/check_docs.py passed locally. Head 89b12f0 pushed those indexes; this continuation update requires one more offline rebuild before the next push. Remaining: verify CI on the final head, coordinate integration and verify the installed app. Preserve the active trainer and sweep.

## v172 - 2026-11-08

Active TASK-1033: user requests an Experiments tab for prospective paper trading of any strategy, with live-time predictions, simulated actions and outcomes. This is distinct from the existing optimization experiment workbench. Preserve current sweep and trainer and all simulated-only boundaries. Worktree /Users/mitch/dev/solmargintrader-wt-01a1bc24-experiments, branch agent-01a1bc24-experiments; base PR 117 head 8f4cdbb. The textual-job-lifecycle-specialist owns the separate status-button task in a different worktree. Stele knowledge create for the prospective/paper-only decision is queued as outbox 30def738 after transport closed. Remaining: inspect current prospective forwardtest and paper execution engines; design and implement durable experiments, accessible UI/status, causal and cost tests; integrate concurrent work, delivery, live acceptance.

## v173 - 2026-11-08

Owner also reports the Dry run tab lacks an understandable start control and activity, appears limited to top five presets, and recommends an unproven MACD strategy that cannot be selected. The textual-job-lifecycle-specialist owns Dry Run UI and status in its isolated worktree; preserve live trading defaults and avoid claiming backtest success without evidence. Integrate its work with TASK-1033 prospective paper experiments and the pending sweep recovery PR.

## v174 - 2026-11-08

The prospective Experiments tab and detached paper runner are implemented in /Users/mitch/dev/solmargintrader-wt-01a1bc24-experiments. The runner records causal 1, 5 or 30 minute calls under a unique experiment and frozen code fingerprint; it simulates non-overlapping 1x positions with configured round-trip costs and $1000 default paper capital. It never sends orders. An isolated real-feed smoke run recorded three calls and one resolved result, then stopped cleanly. Eleven targeted tests pass. No user-selected strategy has been specified, so no persistent user experiment has been started. Remaining: integrate PR 118, update indexes and documentation counts, rerun checks, deliver and verify the installed console.

## v175 - 2026-11-08

PR 118 merged at 259005c30976a0e9cce45cd2c8135586ce755f81 after its CI passed. The paper experiment branch has integrated the status and historical Dry Run changes and preserves both continuation records. The original SOL sweep segment contains no rankable positive hourly candidate because the hourly candles have gaps; its highest positive rankable daily strategy is vol_regime, which is not evidence that it will work on minute candles. Remaining: validate the combined branch, refresh its offline indexes, finish delivery, and verify the loaded UI before starting a prospective paper run.

## v176 - 2026-11-08

Started prospective paper experiment 7f7057972ebb32c82fcadf75 from /Users/mitch/dev/solmargintrader-wt-01a1bc24-experiments as PID 44729. It uses SOL, vol_regime with the highest eligible daily-sweep parameters, a five-minute horizon and $1000 paper capital. It runs on minute candles, so the daily result does not establish minute profitability. Its first prediction was recorded and its balance remained $1000. No real order was sent. Preserve the worktree while this detached process runs, and check its current lock and status before asserting it remains active.

## v177 - 2026-11-08

Coinbase connector work in /Users/mitch/dev/solmargintrader-wt-coinbase-01a1bc24, branch agent-coinbase-01a1bc24. Stele task creation queued as outbox 2af4599e because transport closed. The user supplied /Users/mitch/dev/solmargintrader/llms/docs.cdp.coinbase.com.llms-full, asked to sync Coinbase alongside existing wallets, download markets, and ultimately test a real SOL/USDC buy. The intended live test was initially $0.03, but Coinbase reports a 1 USDC minimum. The owner then requested transferring around $5 of native SOL from another wallet to Coinbase. Coinbase UI explicitly showed a Solana-network native SOL receive address and 0.001 SOL minimum. The saved Solana wallet has only 0.025544731 SOL, roughly $2.27 at the observed quote, plus JUPSOL; it cannot supply $5 of native SOL while reserving fees. No transfer or order was submitted. Await source wallet/permission to convert JUPSOL; never guess or reuse an ambiguous submission. The $1000 is only simulated experiment starting capital. The connected Coinbase MCP has read access to the default portfolio but does not by itself provide reusable app authentication; determine a secure supported app-level connector without copying OAuth tokens. Market public API supports cursor pagination. Preserve existing wallets, no secret output, and no surprise funding trades.

## v178 - 2026-11-08

The owner authorized converting JUPSOL to SOL. The Jupiter UI has a 0.03 JUPSOL to SOL quote prepared and awaits the owner's wallet approval; no swap, transfer or order has been confirmed. Verify the resulting chain transaction before continuing. The connected Coinbase MCP provided a complete 38-account read snapshot, saved separately in mode 600 under the user's SolTUI config; future refresh requires separate app authentication. Public Coinbase market retrieval produced 929 spot, 100 future, 1,873 equity and 5,665 global derivative entries. Equity pagination stalled, so the catalog is explicitly incomplete and saved separately from the prior snapshot. Staked Coinbase holdings may be excluded. The requested 0.03 SOL/USDC buy is below the reported 1 USDC minimum; do not increase the order without authorization. The received SOL is not USDC.

## v179 - 2026-11-08

The Coinbase snapshot now includes the authorized portfolio breakdown, including separately identified staked spot positions, in addition to trading balances. The app refresh uses the official CLI and requires a separate read-enabled API key. The current connected MCP authorization does not provide app credentials. Focused connector and button-registry tests pass. Code is a checkpoint in draft PR 119; integrate concurrent UI work, add installed acceptance and finish delivery after CI.

## v180 - 2026-11-08

PR 120's macOS CI exposed an invalid paper_experiment command namespace and missing parity fixtures. The integrated Coinbase branch includes the paperexperiment rename and safe fixtures for both paper and Coinbase commands. PR 119's unchanged extension browser smoke also failed two startup checks once, while the same checks passed on PR 118 and PR 120; rerun on the final head and investigate any repeat. Rebuild offline indexes and wait for final CI before merging.

## v181 - 2026-11-08

Coinbase sync and market download write local snapshots, so their registry entries set read_only=False. The last-snapshot command remains read-only. This prevents read-only command surfaces from treating downloads or refreshes as passive actions. The registry metadata has a focused regression test.

## v182 - 2026-11-08

PR 119 merged as 2f649690c38acaac8bee36c299ce325679b7cd30 after required CI passed. The user requested using Jupiter's trading MCP for the JUPSOL to SOL swap and identified /Users/mitch/.env as the API-key location. The configured server was not exposed as a session tool, but its HTTP MCP endpoint accepted read-only requests. swap_get_order quoted 0.04 JUPSOL to about 0.0487 SOL. swap_execute_order requires a signed transaction; the Jupiter CLI listed no signing keys and Coinbase CDP did not control the source address. No swap or transfer was sent. A Codex MCP configuration inspection inadvertently exposed the Jupiter credential in tool output. The owner must rotate that credential. Do not copy, print, import or inspect the project's Solana private key. Preserve the running paper worker and Signal trainer. The current interactive console still predates delivery.

## v183 - 2026-11-08

The owner configured the Jupiter CLI signer. Its public address matched the intended Solana source wallet. A Jupiter MCP swap order passed exact-transaction simulation and checks of all existing owner token accounts, SOL reserve, fees, and signed message. One submission swapped 0.04 JUPSOL for 0.048699999 SOL; Solana finalized signature 615rbyxBnwRVgYyR8tCSuuprAewbhwmNbELbNbABX8VqkSGtAzqV4oPzJcohVEYvhEccrgkFedeUcT2MFL65WncQ. A separately decoded and simulated payment sent 0.055834729 SOL, approximately $5 at the live quote, to the verified Coinbase Solana address. Solana finalized signature 2447YyVGsyr2K9NxikpcKJGTxfTZ32NncmZTWSBHzjhc5yFkSfNQbTunKxtagKnRxqPxy35Z6hPXBj1P7yZAem36. Coinbase showed the deposited amount available, and the local Coinbase account snapshot was refreshed. Receipt journals are in /Users/mitch/.config/soltui/jupiter-transactions. Stele knowledge and task updates are queued as outbox ff51a048 and 006238b9. The requested $0.03 SOL/USDC buy remains below the 1 USDC minimum and was not submitted; deposited SOL is not USDC. The exposed Jupiter API credential still needs rotation unless the owner has already rotated it.

## v184 - 2026-11-08

The owner authorized any Coinbase transaction as the live connector test. Coinbase filled order 8039c0bd-d54a-49c8-86b5-cbc1160a7084, selling 0.01232907 SOL at 89.19 USDC for 1.0897330855203 USDC after fees of 0.0098966677797 USDC. Order lookup confirmed FILLED and one fill. The connected Coinbase account snapshot was refreshed. The receipt is /Users/mitch/.config/soltui/coinbase/orders/8039c0bd-d54a-49c8-86b5-cbc1160a7084.json. The prior queued Stele entries ff51a048 and 006238b9 were cancelled as stale; TASK-1037 now reflects the filled order, and KNOW-1039 records its evidence. The app's independent read-enabled credentials and full equity-market catalog remain open. No further real order is authorized by this test.

## v185 - 2026-11-08

The owner saved a Coinbase API key in /Users/mitch/Downloads/coinbase-key.json. The Coinbase CLI imported it and the file permissions were restricted to mode 600. Coinbase reports the key has View, Trade and Transfer permissions; this sync feature needs only View, so the owner was advised to restrict it. The first authenticated refresh failed because the CLI omits has_next and cursor on its final balance page. sync_account now accepts that form only when the reported size matches the page and no cursor is present. The real SolTUI command refreshed one portfolio, 38 trading accounts and one portfolio breakdown. Regression tests preserve the old snapshot on inconsistent data. Remaining: deliver the fix and verify the loaded console. The equity-market catalog remains incomplete.

## v186 - 2026-11-08

The owner clarified that SolTUI should eventually trade real money and needs Trade permission. The earlier suggestion to remove Trade permission was too broad. The present SolTUI Coinbase account module only reads account data, and the confirmed Coinbase test order used the separate connected trading service. Keep the existing key and its permissions. The owner has not authorized automatic live trading merely by enabling the Trade permission. Preserve the dry-run default and existing risk controls. The intended first live trading workflow needs clarification.

## v187 - 2026-11-08

The owner chose to build a manual Coinbase order screen now. Stele TASK-1042 tracks the work, and KNOW-1043 records explicit review, disarmed defaults, validation, reconciliation and no automatic resubmission. Finish the authenticated account-sync fix, then implement and verify the manual screen. The owner did not request another live order or authorize automatic trading.

## v188 - 2026-11-08

The owner also requested a complete, retained list of Coinbase trading pairs and Jupiter support for manual transactions involving Solana coins unavailable on Coinbase. TASK-1045 tracks the complete spot catalog and TASK-1044 tracks the Jupiter venue. Stele claim and dependency writes for TASK-1045 are queued as outbox f3235951 and 99dcf151. Preserve strict venue identification, mint and amount validation, disarmed defaults, exact transaction verification, and no automatic resubmission after an ambiguous outcome. No new real transaction was requested for testing. The manual Coinbase screen and backend are under active implementation in /Users/mitch/dev/solmargintrader-wt-coinbase-manual.

## v189 - 2026-11-08

The owner requested an option to silence order confirmations once selected, for fast manual orders and automation. Keep this option off by default; retain venue validation, order limits, submission journaling and the uncertain-outcome lock. This supersedes the prior mandatory per-order review decision in KNOW-1043. Its update is queued as Stele outbox f3e6ff65 after the transport closed. No new live order was authorized as a test.

## v190 - 2026-11-08

The owner requested F5 to run optimized historical backtests from the beginning and then recording forward tests for every strategy, coin, and timescale. F8 should transfer the selected strategy into Experiments with editable defaults. Experiments need a live-run questionnaire for account, capital, and keys. The owner also requests Jupiter cost modeling, leverage up to the venue's actual maximum, and both long and short experiments and orders. Jupiter spot swaps and perpetuals are distinct venues; identify the product and current venue limits and fees before execution. Do not claim arbitrary token swaps, live perps, or backtest coverage until implemented and verified. Existing dry-run defaults and uncertain-submission protections remain. The Coinbase manual-order PR 125 is in CI. The F5/F8 UI investigation is assigned to the Textual specialist in this worktree.

Stele task creation for the new scope is queued in outbox 32c40404 because the Stele transport closed.
The sourced Jupiter spot versus perpetual cost distinction is queued in outbox a5df844f.

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

TASK-1049 adds a daily recurring bot optimizer, a detached worker and dedicated launchd recovery watchdog. Stop disables recovery and completes the current optimizer call without killing other workers. The scheduler only enables per-coin adoption when the integrated backend declares its safe capability; triangle remains evidence-only. Status exposes last and next runs, partial results and errors. Tests used mocked service calls; the production scheduler has not been started. Integrate with the per-coin backend and verify launchd before claiming it is running.

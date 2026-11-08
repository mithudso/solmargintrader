# Work continuation

Version: 71
Delta: v70 to v71; four-child evidence gate accepted and independent source review completed.

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

## v70 - 2026-11-08 (Four-child /dr start)

Active: TASK-905; research stage TASK-907, install stage TASK-908, publication/delivery stage TASK-909.
Worktree: /Users/mitch/dev/solmargintrader-wt-01a1b5ef; branch agent-01a1b5ef; base afaa03a.
Scope: standard-depth /dr on Conditional nonlinear information transfer; Finite-sample dependency uncertainty; Lag-selection multiplicity; Directed graph preservation. Parent: Uncertainty-aware nonlinear crypto lead-lag. Prior TASK-808 is complete; reuse exact parent evidence without claiming this explicit child depth was already done.
Constraints: research only; no trades, keys, services, broad source rewrites or shared-checkout edits. Three independent source origins per concept; negative searches; exact readable source spans; deterministic and semantic research-gate/v4 checks for all assertions; preserve paid supported judgments. Do not infer executable SOL profitability from dependence, significance or graph stability.
Completed: read routing and /dr instructions; semantic hub lookup found parent claims and reference; verified shared checkout contains unrelated work; created isolated worktree from fresh origin/master. Research worker owns only canonical new run and its evidence; root owns project records, installation, audit and Git delivery.
Remaining: actual research/gate; qualified installed skill; finish tree/site projections; independent audit; tests, exact owned commits, PRs, CI, final merges and owned cleanup.

## v71 - 2026-11-08 (Four-child evidence accepted)

Completed: actual standard-depth native adapter adaptive research on all four named children. Forty-nine structured claim records (13 conditional, 13 finite-sample, 7 lag-selection, 16 graph) and 24 auxiliary assertions passed the final research-gate/v4: 56 SUPPORTED and 17 nonassertions. Packet SHA: 80027ebbee91025d1506d54460828fdc6d1a6e22d079d8ad735a12055803d8db. Validation SHA: 3edae8b09ac3f75c47e8ffaed95d898bb817db75ee8bf3f3e0b95c81f845c30c.

Independent source review: three original research groups per child, negative searches, 81 structured evidence spans and 32 bound snapshots. One bounded combined repair fixed seven first-review failures and six context gaps, with overlap between them; 60 judgments reused and only 13 changed pairs reviewed. Scientific statements and sources remain scoped to their actual studies. No measured five-minute SOL strategy is established.

Root report reproduces ten exact accepted assertions and labels the experiment proposal. Its identifiers were rebound to the final packet after two source-span repairs changed canonical IDs. Public-safe selected claim index and gate receipt are in research/nonlinear-lead-lag-children/. Raw sources and judge transcripts remain private in the canonical run /Users/mitch/.global-ai-hub/research/nonlinear-lead-lag-four-children-task905.

Checks: 872 SolTUI tests ran (870 passed, 2 skipped); 34 Mongo tests ran (17 passed, 17 server/driver skips); 361 extension tests passed; offline oscillating dry run closed one positive round trip. Archived figure check passed 1084 transcription/recomputation checks, not a new market experiment. Initial 900-test backtester run had only the expected index-staleness failure from changed workflow records; regenerate the offline index and rerun after final documentation.

Stele transport closed after stage creation. Exact lifecycle writes queued: claim TASK-907 in 5e16424f; complete TASK-907 in 5532828f; claim TASK-908 in 509bdd0d. These identifiers are recovery receipts, not confirmed graph closure.

Remaining: finish supported skill render/metadata qualification and delivery; exact stable runtime activation; adapter finish and four child projections; independent publication audit; final root records/index checks, PRs/CI/merges and owned cleanup. Preserve original dirty checkouts, shared index differences and paused services.

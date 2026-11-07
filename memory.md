# Work continuation

Version: 12
Delta: added the extension side of the soltui command bridge (workstream X) and the owner's load-path finding.

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

Target: soltui command bridge, extension side. Branch ext-soltui-bridge, worktree /Users/mitch/dev/smt-wt-ext. Stele MCP was unreachable, so facts below are not yet in the graph.

Completed: `soltuiCommands` and `soltuiCall` in the registry (`extension/src/core/soltui.js`) over an injected `deps.soltui` transport; service-worker transport (`src/bg/soltui-transport.js`, `connectNative`, one short-lived port per request); node transport (`tools/soltui-transport.js`, same 4-byte framing); manifest `nativeMessaging` permission; dashboard SolTUI panel (`src/ui/soltui-panel.js`); 1-minute `solmargintrader-soltui-build` alarm and the reload gate (`src/core/autoreload.js`, `enginePending` in `engine.js`); fixtures `e2e/fixtures/`; tests `soltui-bridge`, `autoreload`, `soltui-parity`, `soltui-panel`; e2e extended (host manifest written into the Chrome for Testing profile's NativeMessagingHosts dir).

Facts to keep: (1) The owner's unpacked load path for extension pnokcppamfghgaimmmghoegjllhonhbh is /Users/mitch/dev/solmargintrader/extension, in Chrome Beta (`Google/Chrome Beta/Default/Secure Preferences`, `extensions.settings.<id>.path`). Branded Chrome (stable) has no entry. The installed permissions there are alarms and storage, so the owner must reload the extension once for nativeMessaging. (2) `chrome.runtime.reload()` fires onInstalled with reason update, and `handleInstalled` forces `armed: false` on every update, so an auto-reload disarms the grid; the kill switch and mode are kept. (3) The reload runs inside the engine store lock and holds it until the worker dies. (4) The soltui response is returned as `result` (the CLI prints it, the API nests it under `result`), never spread over the message response. (5) `test/surfaces.test.js` scans src/ui/*.js for the literal `type: '<word>'` as a message name, so UI code must set element kinds by assignment. (6) Fixtures live in e2e/fixtures, not test/, because files under test/ run under `node --test`.

Remaining: wait for the Python host (parallel workstream) on origin/master, run the e2e against the real host, docs counts, check_docs, PR, CI, merge, fast-forward the live checkout.

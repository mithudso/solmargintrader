# Work continuation

Version: 30
Delta: v29 to v30; preserve five-minute perps recovery records and upstream continuation.

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

## v28 - 2026-11-07 (Five-minute leveraged perps full-suite)

Target: research five-minute SOL Jupiter Perps directional signals and adverse-path survival. Task TASK-808. Private worktree /Users/mitch/dev/solmargintrader-wt-01a1b5ef, branch agent-01a1b5ef at c01412a. Preserve all shared checkout and other worktree changes.

Completed: read project instructions and routing index; full-suite is folded under llms-txt-tooling/references/full-suite.md. Fetched KNOW-656 (dated cost mechanics) and KNOW-657 (data/execution gap); created decision KNOW-809 separating terminal direction, barrier survival and net expectancy. The stele-search agent failed because its fixed gpt-5.4-mini model is unsupported; direct named-node reads are the fallback.

Constraints: research only, no trading or execution/config changes. No keys, signing, daemon restart, inference or indexing services. Full-suite saturation and gate receipts must be earned, never inferred from artifacts.

Remaining: map coverage and scored gaps; research current venue and short-horizon predictive evidence; compile source packs and rollup; independent audit; offline indexes/docs checks; commit/PR/CI/merge and remote verification.

## v29 - 2026-11-07 (Full-suite preparation and audited private draft)

Completed: full canonical-tree inventory, 30 scored candidates across five neighborhoods, 23 HAVE and seven distinct above-threshold gaps. Canonical CVS checker passed all 30 rows. Verified 47 prior canonical SUPPORTED claims against 114 bound snapshot spans with zero missing/hash/offset failures. Seven preliminary scouts preserve leads, not evidence. TASK-810 complete; research TASK-811 and parent TASK-808 remain unfinished.

Current sources: refreshed four official Jupiter JLP pages and one exact-five-minute Binance empirical paper into private source library. KNOW-813 records current minimum linear-impact fee, jump-rate borrow curve, rolling flow imbalance and dual execution paths; KNOW-656 now carries a current-source caveat and contradicts edge. Do not treat the August fee-only model as current execution pricing.

Private draft: /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-task808-unpromoted/FIVE-MINUTE-PERPS.md (SHA256 ceef7f86d2aa505eff5a484f66eb7a2caae3f8650fad0374e19cf2245bf977b3) and calculated-scenarios.json (SHA256 c8fae31cce7f1edc7eaefdde6bbbfb6a609515f07597d7c785636109a720ecd4). Independent research-contract-auditor found no material source/math/scope errors; verified five snapshot hashes, 15 leverage scenario values, five symmetric probabilities and one asymmetric probability. This is a scoped synthesis, not a completed full-suite or v4 publication receipt. No profitable five-minute SOL strategy is claimed.

Blocker: python3 /Users/mitch/.global-ai-hub/scripts/dr_run.py check exits 1: retired research sink still present: /Users/mitch/.research. Installed /Users/mitch/.claude/commands/dr.md says to stop and report this condition. Directory contains about 23 MB of unrelated older local-model research. User async approval is pending for intact archive to /Users/mitch/.global-ai-hub/research/.legacy-archives/research-20261107-task808. Preserve it until answered. No new /dr init/research/gate/render/finish/tree write or service startup.

Verification: system Python lacked pandas; existing /Users/mitch/.venvs/soltui/bin/python ran research/verify_numbers.py successfully (1084 archived figures; not a new performance test). scripts/check_docs.py passed with counts 734/313/33/682. No product code changed; new scenario invariants and independent recomputation passed. Private reuse-only pack: /Users/mitch/.global-ai-hub/llms-concepts/five-minute-perps-inherited-v4.llms/. It retains 47 exact inherited supported assertions and 47 FTS5 rows. It is a private draft, not a new researched family: semantic/agent tests are absent, and facts-format lint conflicts with exact-proof reuse. The run-state receipt records all limitations. Remaining: on approved archive, run adapter research/gates on seven gaps, quality audits, final packs/rollup/index/tree steps and saturation gates. Preserve inventory and successful source reads. Repository recovery delivery is tracked in TASK-808; verify its PR status rather than assuming merge.

## v30 - 2026-11-07 (Private reuse pack and recovery checkpoint)

Completed: private source-bound reuse pack retains all 47 unchanged supported assertions. Keyword FTS5 has 47 rows and four nonzero query checks. Vocabulary and digest repairs pass their relevant checks; exact long assertion formatting still conflicts with facts lint and remains an explicit qualification limit. Semantic indexing and agent tests were not run. No source-derived new research draft is staged for the public repository.

Current recovery task: integrate origin/master 3cc9b44 without losing the other session's continuation records, refresh three offline indexes, commit and push the task branch and open a draft PR. Parent TASK-808 remains unfinished. User archive decision remains pending. Do not run new /dr work or alter /Users/mitch/.research before the answer. Delivery receipt belongs in TASK-808; all research stages after preparation remain owed.

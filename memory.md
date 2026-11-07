# Work continuation

Version: 45
Delta: v44 to v45; compound default costs and liquidation are Hyperliquid's (v44 is the Backtest tab, wallet and table titles).

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

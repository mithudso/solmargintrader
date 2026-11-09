# Signal Desk — Chrome extension design option

Version: 1.2
Delta: v1.1 to v1.2; all three council advisors verified 13 corrections with no residual findings; standalone browser acceptance passed.
Owner: repository owner; proposal prepared by Codex, 2026-11-08.
Source snapshot: `2ca304188c71bf258be5d1acb6a60ee5eefca8e9` (remote default branch at investigation).

## Recommendation

Make the dashboard a calm research and monitoring desk with four permanent destinations: **Live signals, Backtesting, Forward testing, Bot monitor**. Preserve registry discoverability as **All tools**, with policy-blocked and archived mutators visibly unavailable, and compose purpose-built screens over the existing commands. The extension already has extensive SolTUI parity; most of this work is information design and workflow composition, not building another backend.

Use the name **Signal Desk** as an optional workspace label. Keep SolMarginTrader as the product identity. This is one proposed interface; the installed extension is unchanged. The standalone mockup contains synthetic examples, no operational connection, and no performance evidence.

The benefit is continuity: select a strategy once, inspect its historical results, stage a paper trial, and follow its evidence and worker health without rebuilding context in separate generic forms. Pleasure comes from readable charts, quiet feedback, understandable explanations and reliable navigation.

## Capability map

The source audit found 147 native SolTUI registry commands and 35 extension commands at the snapshot above. These are code counts, not current installed-host acceptance. The dashboard discovers the installed registry dynamically. Its nine grouped native workspaces plus legacy sections duplicate destinations and make common tasks compete with expert tools.

Current navigation and generic result rendering: /Users/mitch/dev/solmargintrader/extension/src/ui/dashboard.html:15 and /Users/mitch/dev/solmargintrader/extension/src/ui/workspace-model.js:2 (`WORKSPACES`, `filterCommands`, `resultTables`). Registry parity and browser-native lifetime contract: /Users/mitch/dev/solmargintrader/docs/EXTENSION-TUI-PARITY.md:7 and /Users/mitch/dev/solmargintrader/docs/EXTENSION-TUI-PARITY.md:47.

Classification key: **E** = current extension/native bridge capability; **B** = elsewhere in repo, needs a scoped bridge; **P** = proposed composition or feature; **A** = archived; **U** = implemented or described but live acceptance unverified/blocked. A family can carry multiple labels. Source existence is not a claim that the installed application has exercised it live.

| Capability family and status | Proposed destination and treatment | Current source / contract |
| --- | --- | --- |
| E: CPCV backtests, roster sweeps, run status/cancel; paper leverage, short and confidence controls | Backtesting: run setup, queue, cost-aware comparison, provenance and paper handoff | /Users/mitch/dev/solmargintrader/soltui/commands.py:1111; /Users/mitch/dev/solmargintrader/soltui/README.md:158 |
| E: prospective forecasts, per-coin trials, histories, optional tuning/adoption | Forward testing: immutable trial identity, pending/resolved ledger, paper trade eligibility | /Users/mitch/dev/solmargintrader/soltui/README.md:175 |
| E: recorder prices, predictions, agreement score, eligibility floors and observed score tape | Live signals: source age, explanations, excluded-vote reasons and a stable chart | /Users/mitch/dev/solmargintrader/docs/LIVE-PREDICTION-SCORE.md:3; /Users/mitch/dev/solmargintrader/extension/src/ui/dashboard.html:58 |
| E: compound metric catalog, weights, regimes/gates, closed-5m scoring, training/autopilot | Live signals detail; Forward testing; Bot monitor for workers and adoption history | /Users/mitch/dev/solmargintrader/soltui/commands.py:1595; /Users/mitch/dev/solmargintrader/soltui/README.md:156 |
| E: grid/DCA/triangle simulations, forward stream replay, rank/audit/optimize/schedule | Bot monitor plus bot research detail; label simulations and historical replay separately | /Users/mitch/dev/solmargintrader/soltui/commands.py:2556; /Users/mitch/dev/solmargintrader/soltui/README.md:243 |
| E: typed experiment search, budget preview, workers/controls, immutable candidates, sparse heatmaps, final holdout, CSV comparison | Research library → Experiments; frequent experiment workers appear in Bot monitor | /Users/mitch/dev/solmargintrader/soltui/commands.py:2888; /Users/mitch/dev/solmargintrader/soltui/README.md:305 |
| E: cards/source/roster, combinations, presets, Top 5, batch/queue/cumulative, rule readouts and indicators | Backtesting detail and Library; distinguish executable strategies from specification-only cards | /Users/mitch/dev/solmargintrader/soltui/commands.py:570; /Users/mitch/dev/solmargintrader/soltui/README.md:151 |
| E: bar-by-bar replay, reset/step/end; cached dry-run recommendation/spawn | Backtesting → Replay; historical replay never masquerades as prospective evidence | /Users/mitch/dev/solmargintrader/soltui/commands.py:1191; /Users/mitch/dev/solmargintrader/soltui/README.md:160 |
| E: recorder status/ensure and explicit queue cache fetch; B: advanced minute/tick/bulk/gap audits | Data health detail; explicit fetch action; advanced data tools require dedicated adapters | /Users/mitch/dev/solmargintrader/soltui/commands.py:3030; /Users/mitch/dev/solmargintrader/docs/SCRIPTS.md:35 |
| E: broad public-wallet discovery, portfolio snapshots/changes/notices; Coinbase accounts/catalog | Wallets: per-chain sections, coverage and snapshot times; no silent deep scan | /Users/mitch/dev/solmargintrader/soltui/README.md:365; /Users/mitch/dev/solmargintrader/soltui/commands.py:2451 |
| E: source-separated P&L, realized/unrealized, costs, curves, drawdown, attribution | Wallets & results: retain separate paper, dry-run, wallet and historical LP sections | /Users/mitch/dev/solmargintrader/soltui/commands.py:2182; /Users/mitch/dev/solmargintrader/soltui/README.md:344 |
| E/U: guarded manual Coinbase orders and manual Jupiter spot preview/submit/reconcile; explicit quick modes already exist | Wallets & orders: preserve the existing per-path authorization/confirmation policy and preview identity; no confidence-based auto-promotion | /Users/mitch/dev/solmargintrader/soltui/commands.py:2204; /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:1 |
| E: browser holdings, quote-only swap handoffs, quoted/modeled pool discovery and alerts | Wallets, quotes and alert center; passive pool lookup secondary; retired scout results get dates/archive labels | /Users/mitch/dev/solmargintrader/extension/README.md:27; /Users/mitch/dev/solmargintrader/extension/src/core/commands.js:337 |
| E/U: experimental execution grid, levels/capital/plan, journal/fills/carry/CSV, rails and unknown intents | Advanced execution detail, visibly dry-run/disarmed; Trigger live signing remains blocked | /Users/mitch/dev/solmargintrader/extension/src/core/commands.js:178; /Users/mitch/dev/solmargintrader/extension/README.md:49 |
| E: document catalog/read/edit/export, shared research settings and public addresses | Library & editor and Settings; guarded saves, protected research; default UI-local catalog filtering; every docs.search invocation is explicit | /Users/mitch/dev/solmargintrader/soltui/commands.py:1912; /Users/mitch/dev/solmargintrader/docs/EXTENSION-TUI-PARITY.md:24 |
| A: discontinued Aero liquidity manager/scout/positions/experiments and retained controls | Archive: historical records only in normal navigation; no routine Resume control or income nudge | /Users/mitch/dev/solmargintrader/liquidity/CLAUDE.md:3; /Users/mitch/dev/solmargintrader/soltui/commands.py:1799 |
| B: complete standalone executor gates, soak, status, journal, kill/reconcile via CLI/loopback API | Bot monitor → proposed read-only native executor adapter; manual Jupiter bridge already reuses verifier machinery | /Users/mitch/dev/solmargintrader/executor/README.md:19; /Users/mitch/dev/solmargintrader/executor/README.md:46; /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:25 |
| B: pairs/cointegration, cross-asset and PBO/DSR research, perturbation, geometry, turnover/rotation audits | Advanced research catalog: explicit scoped job adapters; no arbitrary script launcher | /Users/mitch/dev/solmargintrader/docs/SCRIPTS.md:32; /Users/mitch/dev/solmargintrader/backtester/README.md:367 |
| B: derived Mongo mirror of bars/cards/decisions/results/docs/test evidence | Optional data inspector showing query provenance and freshness; original files remain authoritative | /Users/mitch/dev/solmargintrader/mongo/README.md:3 |
| E: extension CLI/HTTP and native shared command surfaces | Expert All tools and API documentation; UI keeps actions in current registries | /Users/mitch/dev/solmargintrader/extension/src/core/commands.js:1; /Users/mitch/dev/solmargintrader/docs/API.md:1 |
| P: composed screens, version-bound handoff, saved comparison sets, activity tray, optional side panel and extra adapters | Explicit implementation work below; existing result tables already sort/filter/page/export and chart numeric time series | /Users/mitch/dev/solmargintrader/docs/EXTENSION-TUI-PARITY.md:29; /Users/mitch/dev/solmargintrader/extension/manifest.json:11 |

No source audit here establishes current live fills, a profitable strategy, universal cross-chain execution or unattended live bot support. Manual Jupiter spot and standalone executor verification must not be conflated with extension Trigger signing. The older broad README contains historical claims; the current component instructions govern the discontinued LP service.

## Screens and wireframes

**Full dashboard** is the primary surface. On first use open Live signals; thereafter resume the last workspace and inspect missing connections without starting services. Archive policy applies to the generated All tools fallback too: list `liquidity.resume` and other archived mutators as unavailable with the owner-retired reason. No runnable ordinary control may reactivate that service. Keep the registry source intact; later owner reactivation is a separate scope change.

Keep the four priority destinations visible; a small activity tray persists between them. Secondary navigation contains All tools & library, Wallets & orders, Activity & alerts and Settings. Experiments is a clear Library destination and can be pinned. Archive sits inside Library's advanced section.

**Popup**, about 380px wide, is a glance and resume surface: source age, agreement availability, one important incident, three process counts grouped by lifetime, and four direct workspace links. Never put long-running research or credential entry into a transient popup. It closes on focus loss.

**Optional side panel** is a later, narrow watch view: selected asset, agreement and age, pending paper forecasts, incident count, Open full workspace. It does not replicate comparison tables. It requires new manifest/permission/opening work; the current manifest has no side panel. Opening it must be explicit. Whether its presence renews the native session must be designed and tested, not inferred.

```text
┌─ SolMarginTrader / Signal Desk ───────────────────────────────────────────┐
│ asset · market/source · PAPER / LIVE scope · as-of time   Search · alerts │
├────────────────┬────────────────────────────────────────────────────────┤
│ Live signals   │ Title · purpose · contextual action                    │
│ Backtesting    │ Four meaningful summary metrics                       │
│ Forward testing│                                                        │
│ Bot monitor    │ Chart / run table / forecast ledger  Evidence detail  │
│                │                                                        │
│ All tools      │ Filters · results · explain / compare / stage          │
│ Wallets/orders │                                                        │
│ Activity       │ Persistent activity tray: owner · stage · age · action │
│ Settings       │                                                        │
└────────────────┴────────────────────────────────────────────────────────┘
```

Mockup: /Users/mitch/dev/solmargintrader/docs/design/chrome-workspace/prototype.html. It uses inline HTML/CSS/JS for standalone portability and is **not an installable extension page**. Production implementation follows extension CSP and external script conventions.

## Shared context and interaction contract

Keep asset, venue/data source, strategy/version and selected run visible. Time range is local to its meaning: historical interval, prospective start, or observed chart window. Never carry a backtest's historical end date into a prospective trial as its start without review. Asset changes invalidate incompatible detail and discard late responses from the previous asset; preserve a draft with its original asset label.

A **P: handoff draft** pins parent run ID, strategy/version/parameters, dataset hash, capital, timing, cost assumptions, leverage/short policy and confidence. It is not a new running trial. The owner reviews the prospective start and explicitly starts it using the existing command. A parameter or cost change forks evidence instead of rewriting old observations. Add a shared handoff/preset contract only where the present backend lacks one. Scope saved comparison sets to compatible datasets and show mismatches rather than ranking across incomparable windows.

Distinguish mode at the panel and action: HISTORICAL SIMULATION, PAPER OBSERVATION, DRY-RUN EXECUTION or REAL EXECUTION. Never show one global green pill that implies all components are safe or armed. Wallet value change includes flows and is not automatically trading profit. Missing values remain unavailable; do not convert them to zero.

## Four workflows

### Backtesting result-contract boundary

The existing `backtest.run` summary is narrower than the ideal screen. It currently supplies median Sharpe, Sharpe IQR, positive-path fraction, median net return and aggregate trades. It does not supply all the desired charts or matched benchmark/path details. See /Users/mitch/dev/solmargintrader/soltui/runner.py:38 and /Users/mitch/dev/solmargintrader/soltui/commands.py:1143.

| Screen metric | Current summary support | Required implementation |
| --- | --- | --- |
| Median return, median Sharpe, Sharpe IQR, positive paths, aggregate trades | Existing result fields | Phase 1 displays these with their exact units and aggregation; aggregate trades is not median path trades |
| Per-path net equity/max drawdown, turnover, itemized fees/borrow, path samples and matched costed buy-and-hold | Proposed richer result contract | Phase 2 must add typed backend evidence, dataset/path IDs and matched benchmark assumptions; show Unavailable until provided |
| Saved compatible comparison sets and version-bound paper handoff | Proposed persisted workflow contract | Phase 2; carry evidence identity without changing existing historical records |

The mockup's CPCV drawdown, benchmark, path counts/dispersion and median path trade numbers illustrate the richer proposed contract using synthetic data. They are not fields recovered from current backtest summaries. Never infer them from the median Sharpe or a presentation-only reconstruction.

### Backtesting: investigate → compare → stage

1. Select strategy/version, dataset and interval; inspect available coverage and gaps. Fetch is a separate explicit action. Configure costs, capital, timing, leverage, shorting and confidence; default to existing saved policy and safe product defaults.
2. Run or enqueue a bounded experiment. Keep job owner, completed work, current cell, progress and stop semantics visible. Use only supported controls; keep completed evidence when canceled.
3. Show the existing out-of-sample summary with its exact aggregation. In Phase 2, add typed path drawdown, turnover, fees and matched costed benchmark before broader ranking; CPCV fold dispersion and path counts stay inspectable. Explain leakage/cost assumptions and old-engine results. Never rank specification-only cards as executable.
4. Compare compatible runs and inspect the per-bar replay. Stage a paper trial with the exact version and assumptions. A loss can be valid evidence; the mockup deliberately uses losing examples.

### Forward testing: pin → observe → resolve

1. Review a new or handoff draft. Show live data availability, paper economics, evidence requirements and whether its owner process survives closing the dashboard.
2. Explicitly start prospective paper observation. Keep pending/resolved/void or gap/skipped-trade records separate. Historical stream replay remains labeled replay.
3. Read directional accuracy with numerator/denominator and horizon; show baseline and uncertainty/sample caveat in the full design. Show paper P&L after costs independently. A forecast can continue while its paper trade is blocked by the confidence gate.
4. Inspect the immutable ledger. Fork settings for a new trial; show old and new trials separately. Expose tuning/adoption as existing deliberate operations with receipts, not a background effect of looking at the screen.

### Live signals: observe → understand → inspect

1. Read price/source age, model version, horizon and aggregate agreement together. View source-time-aligned price and immutable score ticks. Show gaps; never repaint previous agreement with later knowledge.
2. Show Strong Buy / Buy / Flat / Sell / Strong Sell with text and color. Current agreement uses equal strategy weights and ±20/±60 thresholds; missing eligible data means Unavailable, not a valid Flat conclusion.
3. Inspect eligible and excluded strategies. Default voting floors are 60% prior measured accuracy and 20 resolved observations for the strategy and voted horizon. Paper trade confidence defaults to 0.80 and is a separate gate. These thresholds do not measure the same quantity.
4. Open the exact trial/evidence or relevant bot. Reading never starts a recorder, trainer, scheduler or trade. Do not place a trade CTA beside a green agreement label.

### Bot monitor: detect → inspect → control precisely

1. Group paper engines, research workers, recorders and execution components. Show heartbeat, last output, feed freshness, last error, next run and execution permission independently.
2. Show **session-owned**, **detached** and **scheduled** lifetime. Closing all dashboards and expiration of native leases can end session replay/checks; detached trainers/experiment workers keep their own lifetime. No universal “runs forever” assurance.
3. Inspect version/config, logs, queue and source-separated P&L. Current-session state is not automatically shared with an independent terminal TUI. Comprehensive executor telemetry is proposed integration work.
4. Offer only the affected component's supported pause/stop/cancel actions. Say what survives: stopping new admission does not close positions or cancel venue orders. Unknown submissions show reconciliation, never automatic retry. Existing arming/rails and reviewed submit policy remain enforced by the owning backend.

## States, accessibility and visual system

Use warm near-white surfaces, deep blue-green navigation, restrained green and red for signed values, amber for attention, and generous spacing around dense evidence tables. Typography: locally available Avenir Next with readable fallbacks; tabular numerals; 15px body and 12px table content in the desktop mockup. Ship a dense/comfortable preference and light/dark tokens only after both receive contrast checks. Visual motion is limited to user-triggered transitions, respects reduced motion, and never animates profit or urgency.

Keyboard navigation, visible focus, semantic controls, labeled filters, accessible charts with text alternatives, focus return from dialogs and Escape dismissal are required. Do not announce every price tick; announce material state changes and provide an opt-in accessible summary. At narrow widths stack evidence panels, retain four primary navigation entries, and allow horizontal scrolling inside genuinely wide tables rather than shrinking text. Final production gate: WCAG 2.2 AA contrast, 200% zoom, keyboard and screen-reader task completion; this proposal does not claim a full conformance audit.

| State | Required behavior / recovery |
| --- | --- |
| First use / no host | Explain native-host absence; retain cached examples only as labeled cached data; offer inspected setup guidance, never silently install/start |
| Fetch or run in progress | Show owner/stage and supported cancellation; repeated submit blocked while active |
| No data / no eligible votes | Unavailable with reason and exact next action; no fabricated price, score, fee or return |
| Price/model stale | Last known source time and independent stale flags; exclude expired votes; preserve last chart with clear stale marking |
| Bridge disconnected | Mark affected actions unavailable; retain timestamped data and unsaved drafts; reconnect read-only before resuming controls |
| Asset switch / delayed response | Clear incompatible state and reject obsolete success and error responses |
| Worker alive but output stale | Separate liveness from freshness; deep link to diagnostics |
| Partial / failed / canceled run | Preserve completed evidence with status and limits; no success toast based on process exit alone |
| Unknown order | Hold admission and reconcile; no retry CTA or success claim |
| Concurrent document edit | Keep refused draft for export; explain the existing pre-read check's race instead of claiming atomic writes |
| Archived service | Historical-only label, source date and disabled operational actions; no ordinary Resume CTA |

## Integration gaps

The current bridge already covers the main workflow families. New work consists of specialized screen composition, typed per-path/cost/benchmark result evidence, persisted comparison/handoff identity, comprehensive standalone executor telemetry, optional advanced-research/Mongo adapters and the optional side panel. The capability map and backtesting result-contract table mark these boundaries explicitly. Missing installed-host access is a connection/setup state; it does not mean the repository lacks that backend capability.

## Rollout and acceptance

**Phase 1 — workflow shell over existing capability.** Consolidate navigation without removing registry reachability; compose four screens and source-specific activity. Default global search uses the current tool registry and `docs.list` catalog plus UI-local filtering. It never calls `docs.search` on keystrokes: every mode of that command invokes an idle index check, and semantic mode can also start Ollama. A deliberate search action must disclose those effects, or a future scoped adapter must offer a truly side-effect-free full-text search. See /Users/mitch/dev/solmargintrader/soltui/README.md:327. Use current allowlisted read refreshes and native session leases; no broad permissions or new runtime dependencies. Acceptance: every current registry family discoverable with archived/policy-blocked actions disabled, main tasks within two navigation steps, data/source/mode visible, unsupported extra metrics show Unavailable, no read view triggers a mutation, no production-default changes.

**Phase 2 — evidence continuity.** Add version-bound handoff drafts and comparison-set persistence where absent; typed provenance contracts, per-path equity/drawdown/trades, turnover and cost breakdowns, matched costed benchmark evidence, pinned-cost previews and accessible result detail. Acceptance: staging never starts a run; incompatible comparisons labeled; modified strategy/cost settings create new evidence; stale/asset-switch races tested; unknown results stay unknown; existing simulation economics unchanged.

**Phase 3 — specialized depth.** Improve experiment heatmaps and bot diagnostics, add explicitly scoped read-only executor integration and optionally Mongo inspection/advanced CLI research adapters. Each adapter adds typed registry commands and preserves secret boundaries. Acceptance: unsupported commands produce honest unavailable states; no arbitrary script execution; sparse cells remain unobserved; executor source state and actual reconciliation are distinguishable from process liveness.

**Phase 4 — optional watch surface and polish.** Trial the side panel only if it improves a real browsing workflow. Add permission and explicit open behavior; define lease/lifetime semantics; verify popup dismissal and recovery. Acceptance: no tool runs because a popup/panel opens; dashboard state survives navigation; keyboard/zoom/screen-reader checks pass; neutral or losing evidence gets equal clarity.

User validation targets for implementation: find one run's net costs in under 30 seconds, identify why a vote is excluded in under 15 seconds, stage the correct paper trial without editing identity, and correctly explain whether an indicated job survives closing the browser. These are proposed usability goals, not measured results or delivery-time estimates.

Official Chrome documentation consulted through Context7 on 2026-11-08:

https://developer.chrome.com/docs/extensions/develop/ui/add-popup

https://developer.chrome.com/docs/extensions/reference/api/sidePanel

https://developer.chrome.com/docs/extensions/get-started/tutorial/service-worker-events

## Council resolutions

Tradeoffs: specialized screens require maintained adapters; keep generated All tools to prevent lost reachability. Fewer primary destinations add one step for less frequent wallet/library work. Rich monitoring needs precise process ownership, not a single reassuring green status. Optional side panel adds permission and lifecycle complexity and should follow the dashboard.

The advisor council evaluates product/accessibility, quantitative research, and operations/extension engineering independently. Every actionable criticism goes into /Users/mitch/dev/solmargintrader/docs/design/chrome-workspace/council-review.md with revision and verification. All three advisors verified the revised option in round 2 and reported zero residual actionable criticisms. Thirteen corrections are recorded, including mobile access, accessible dialogs, unavailable-signal styling, exact fixture evidence, honest result-contract gaps and archive/search policy. The independent verifier also matched the loaded prototype to disk and exercised its workflows at desktop and 390px widths. The option is ready for owner consideration; production implementation remains a separate decision.

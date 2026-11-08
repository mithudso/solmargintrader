# Optimization workbench implementation plan

Version: 3
Delta: v2 to v3; bind numerical runtime, canonical drawdown and control-race review requirements.

Goal: make native optimization inspectable, configurable, resumable and resistant to repeated holdout selection.
Scope: SolTUI simulated grid, DCA and recorded-triangle optimization, plus read-only external result comparison.
Done: all six capabilities are reachable through the shared command registry and UI, meaningful tests and loaded UI acceptance pass, documentation is current, and the final PR is merged.

## Context found

- `soltui/bots.py`: native search currently stores aggregate reports at completion, uses train/test windows and a paired sign-test adoption gate.
- `soltui/bgqueue.py`: existing backtest queue persists whole-job records; its identifiers do not bind all experiment evidence.
- `soltui/commands.py`: shared command registry supplies CLI, API and UI parity.
- `soltui/bots_screens.py` and `soltui/tui.py`: existing progress modal and candidate table provide the entry point.
- `research/perturb.py`: existing one-at-a-time sensitivity is distinct from the proposed observed joint-parameter view.
- External comparison dossier is already delivered in PR 95. The upstream bundle's Smart Linear loop is unfinished and will not be ported.

## Plan A

1. Specify immutable experiment identity, typed spaces, durable cells and final-holdout reservation contracts — needs: existing Bots and queue sources — produces: the contracts below.
2. Implement experiment storage, search preview, observed stability and external import — needs: contracts — produces: foundation module and tests.
3. Integrate native metrics, checkpoints and guarded final validation — needs: foundation and Bots — produces: runner and regression tests.
4. Implement responsive job controls, experiment explorer, search editor, heatmap and import screens — needs: shared APIs — produces: command and UI integration plus tests.
5. Review and exercise loaded behavior — needs: implemented feature — produces: regression and live acceptance evidence.
6. Refresh documentation and generated indexes, then deliver — needs: verified code — produces: merged PR and remote receipt.

## Plan B and ownership

A1 is satisfied by this document and recorded decisions. A2 maps to B1 foundation. A3 maps to B2 runner. A4 maps to B3 lifecycle/UI. A5 maps to B4 independent review and B5 loaded acceptance. A6 maps to B6 documentation and delivery. B1/B2/B3 coordinate against the contract before integrating. B4/B5 follow implementation; documentation follows verified behavior. High-risk: none; all interfaces receive targeted regression tests.

- B1 owns new `soltui/experiments.py` and foundation tests.
- B2 owns `soltui/bots.py`, a new native experiment runner and its tests.
- B3 owns new job controller/screens, narrow changes to commands/UI/help and lifecycle/UI tests.
- Root owns this plan, workflow records, llms compilation and delivery; later documentation ownership is explicit.

## Shared contract

Use `ExperimentStore(root=None)` from `soltui.experiments`, defaulting to `config.CONFIG_DIR / "experiments"`. SQLite transactions persist immutable canonical run specs and unique evaluation cells. Public run dictionaries contain `id`, `status`, `spec`, `summary`, `error`, timestamps and progress. Specs include source, bot, baseline, full candidates, window intervals, code/data/cost fingerprints, Python/NumPy/Pandas runtime provenance and budget. Native source is `native`; imported source is `tradingview`.

Foundation publishes its exact API to the other workers before integration. Required operations are create/get/list runs, update run status/summary, atomic cell upsert with immutable completed evidence, read cells, freeze one candidate, and reserve final temporal intervals atomically. Candidate IDs are stable strings; baseline is index 0. Cells contain candidate ID, coin, split (`train`, `validation`, `holdout`), window key/start/end, status (`completed` or `failed`), nullable rich metrics and an explicit error. Missing metrics stay unknown. JSON must reject non-finite values. Preserve raw simulator/import metrics; experiment drawdown summaries/maps/comparisons use nonnegative loss magnitude with explicit units. Lifecycle transitions use compare-and-set so launch, exit reconciliation and finalization cannot overwrite a concurrent control request.

Typed spaces support fixed values, numeric ranges/steps, explicit choices and positive log spacing. Validate bot domains and leaf simulator configs. Reject bool-as-number, invalid integers, duplicate/unknown fields and excessive valid candidate/evaluation counts. Include baseline once. Preview reports actual valid configurations, coin/window workload and budgets before starting. Do not silently truncate.

Heatmaps use observed train/validation cells only. Hold other parameters fixed when comparing two axes. Missing cells remain missing; no interpolation or manufactured stability. Summaries report coverage and dispersion alongside return and risk metrics.

Import normalized CSV and documented TradingView column aliases. Preserve original units and provenance. Unknown units/costs/fill timing/date intervals cannot be silently normalized or treated as zero. Compare only explicitly compatible contexts; display mismatch reasons. Every contributing row must bind an actual coin and temporal interval before the run can be declared comparable; extra undated rows cannot escape the coverage check. Imports have no native promotion path.

Runner freezes exact candidates, temporal windows and evidence fingerprints. It commits each candidate/coin/window cell before progressing. Resume verifies the stored evidence before reusing cells. A cross-process lock prevents duplicate evaluation/finalization. Pause/cancel are cooperative at cell boundaries and durable; interruption never adopts a partial result. No background service starts without the user action.

Exploration evaluates train and validation only. Freeze the chosen candidate before final validation. Reserve fresh final holdout intervals per bot and coin before evaluating baseline and frozen candidate. Reservations survive search/config/code/cost/data changes and failures. Record exploration exposure before simulation too: a changed window count or duration cannot move an already explored date into a fresh final interval. Exploration must refuse another run's reserved final intervals. Conservatively migrate the known temporal extent of legacy optimization reports, or refuse final validation when legacy history cannot establish unused dates. Freshness refers to recorded local optimization evidence; external/manual prior use cannot be proven absent. Overlap with another experiment is refused; resume permits only the same frozen exact context. Never weaken the existing significance/evidence thresholds. The existing `bots.optimize` route must use the same guards. Triangle replay receives equivalent recorded-data boundaries and checkpoints.

## Acceptance and tests

- Inspect full candidate configurations, return/risk/trade/cost metrics where available, coin/window evidence, failures, provenance and decision reasons.
- Editor rejects invalid/over-budget spaces and displays actual workload before launch.
- Sparse heatmap shows missing points and excludes held-out values.
- Pause, cancel, process death and resume preserve completed cells; mutated historical evidence refuses reuse; concurrent runs cannot bypass locks.
- Repeated searches, changed costs/code/search spaces and overlapping dates cannot reopen spent holdout. Insufficient evidence retains baseline.
- External results preserve units and reject malformed/non-finite rows; incompatible evidence is visibly non-comparable and cannot adopt.
- Registry parity, existing Bots behavior and focused UI tests pass; loaded UI exercises create/preview/browse/control/import without live orders.

## Constraints and open questions

Preserve other sessions and dirty files. No secrets, credentials, live trades, paused research, service restarts or changes to dry-run/disarmed defaults. Standard library first; use the existing Python environment. Implementation agents may refine interfaces together and must record any material change here. No unresolved product decision is required to start.

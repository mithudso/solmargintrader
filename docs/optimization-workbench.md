# Optimization workbench

The Bots tab's **Experiment workbench** keeps complete simulated search evidence. It adds a bounded search editor, candidate/coin/window explorer, observed parameter maps, resumable workers and reported TradingView comparison. It never places an order.

## Start with exploration

Open Bots, choose a bot, then open **Experiment workbench**. Build a search with fixed values, explicit choices, linear ranges with a positive step, or positive log ranges with a point count. Parameters omitted from the search retain the current baseline value. The baseline always appears exactly once.

Preview before starting. Preview validates bot domains and simulator configurations, reports rejected combinations, counts the available coin/window workload and enforces both configuration and evaluation budgets. It does not simulate candidates. The ceiling is 97 configurations including the baseline and 20,000 evaluations. A missing runtime estimate means no measured estimate is available.

Create freezes the full configurations, baseline, windows, evaluation costs, runtime versions and code/data fingerprints. Start evaluates only train and validation windows. Inspect each candidate's full configuration and observed metrics, then drill into individual coins and windows. A failed evaluation has an error and remains distinguishable from a losing result. Metrics the simulator does not provide remain unknown.

All actions also use the shared command registry. For example, this preview evaluates no strategy:

```bash
python3 -m soltui.cli call experiments.preview --json '{"bot":"grid","coins":["SOL"],"windows":6,"window_days":30,"space":{"range_pct":{"kind":"range","start":5,"stop":15,"step":5,"scale":"linear"},"rungs":{"kind":"enum","values":[5,7,9]}}}'
```

Use `experiments.schema` for current baseline values and domain limits. `experiments.create` takes the same search options and returns the frozen run identifier. `experiments.start`, `experiments.get`, `experiments.pause`, `experiments.cancel` and `experiments.finalize` take `run_id`. `python3 -m soltui.cli list` prints their exact parameters.

## Read the evidence

`experiments.candidates` returns full configurations and metric summaries. `experiments.cells` returns individual evaluation records with optional candidate, coin and split filters. Costs, trades and return retain their units; unknown values are not zero. Experiment drawdown summaries, observed maps and comparisons use nonnegative loss magnitude (0.10 means a 10% decline). Native simulator cells and original imported rows retain their raw signed values. Import normalizes drawdown only after its units are explicit. Smaller canonical drawdown is better.

A heatmap conditions on the other parameters and aggregates only observed train/validation cells. It shows coverage, dispersion and missing combinations. A sparse set of tested points is not an interpolated performance surface. Final holdout metrics never participate in heatmap or exploration rankings. `experiments.heatmap` supports explicit axes, metric, fixed settings, coin and split.

## Pause, close and resume

Explicitly launched experiments run in a separate process. Closing the workbench or console leaves that worker running. Pause and cancel request a stop after the current evaluation commits. The screen reports the request until the worker acknowledges it; it does not claim that a thread or process stopped immediately.

Each completed evaluation is durable. A resumed run verifies its frozen code, data, cost and window context before reusing evidence. A changed historical input refuses reuse. A process lease prevents duplicate workers; a dead worker becomes interrupted and can be resumed. Diagnostic failures and the worker log tail are visible through `experiments.get`. No worker starts merely because a module is imported or a saved experiment is listed.

The default experiment directory is the SolTUI configuration directory's `experiments/` subdirectory. Keep its SQLite database and job evidence together. Deleting this local history discards the system's ability to recognize previously used dates.

## Final validation and adoption

The newest half of the usable chronological windows is final holdout. The older half is divided into train then validation (rounding leaves at least one training window). With only two usable windows there is train and holdout, with no validation window. Recorded triangles use the requested newest usable hour windows within the newest two recorded day files; bar window lengths do not turn into triangle day windows. Triangle replay keeps unavailable percentage drawdown and exact total-cost metrics unknown.

Exploration does not adopt settings. Final validation freezes the training-selected candidate and reserves its final temporal intervals before evaluating it beside the baseline. It retains the existing one-sided sign test, positive median improvement and minimum ten decided cells. Finalize defaults to reporting only; saving native bot settings requires explicit adoption and all evidence gates to pass. A completed reliable native result can be reviewed and then explicitly adopted without new simulations; its frozen context and current baseline must still match.

The ledger records exploration exposure and final reservations per bot and coin. Changing the search space, costs, code, data or window geometry cannot make overlapping dates fresh. Interrupted final validation can resume only its exact frozen candidate/context. A failed attempt does not free the dates for another candidate. Known pre-workbench optimization evidence is handled conservatively rather than certified untouched by an empty new ledger.

Freshness means unused in the recorded local optimization history. The application cannot establish that a person or another tool has never inspected those dates. New forward observations can supply genuinely later evidence. Insufficient, failed, stale or reused evidence keeps the current configuration and explains why.

The older **Auto-optimize** action also uses these durable evidence and final-validation safeguards. Its report keeps the familiar decision and saved-setting details.

## Import reported TradingView evidence

Import a local CSV through the workbench or `experiments.import`. Supply explicit metadata for units, bot/script, coin, dates, interval, currency, data source, fees, slippage, borrow assumptions and fill timing when known. Unknown provenance remains unknown. Imports retain original columns, reported values and a CSV content hash. Both normalized result columns and the inspected optimizer's all-trades export aliases are supported. Long/short-only columns are not silently pooled into all-trades results.

Rows without coin/date bounds remain visible as reported evidence, but do not become dated native evaluation cells. Imported runs never execute a strategy, reserve native holdout, adopt settings or become a native winner.

`experiments.compare` takes `left` and `right` run identifiers. It displays side-by-side evidence and explicit compatibility reasons. Matching labels alone cannot override different actual coin/window coverage. Missing or conflicting units, data, costs, fill timing or strategy assumptions prevent a comparable verdict. Return percentages are normalized only when units are explicit; currency profit is not invented as a percentage return.

## Verification and implementation

See [the implementation plan](optimization-workbench-plan.md) for ownership and acceptance criteria. Native optimization remains simulated; existing dry-run and disarmed defaults remain in force. The modules and regression tests are listed in [the codebase overview](codebase-overview.md).

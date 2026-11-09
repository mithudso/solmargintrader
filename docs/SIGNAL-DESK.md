# Signal Desk

Version: 1.0
Delta: implement the council-reviewed four-workspace Chrome interface.

Signal Desk is the extension's default full dashboard in version 0.5.0. Its light/dark interface
puts Live signals, Backtesting, Forward testing and Bot monitor in permanent navigation. The
popup provides read-only glance information and direct links. No service, training job or order
starts because a screen opens.

## Live signals

Choose a view asset. Read the existing recorder's price, source age, saved predictions and
aggregate directional agreement. Every ten seconds, visible prediction evidence refreshes even
when Follow stream is off; Follow stream separately refreshes recorder reads every five seconds.
Expired/future calls cannot vote. Missing evidence is Unavailable, not a valid neutral zero.

The strategy table includes prior strategy accuracy/sample counts, each horizon's readout, eligibility
and exact raw evidence. Filter is local and survives refreshes. Why this score explains equal
strategy weighting and the ±20/±60 labels. Default eligibility floors are 60% accuracy and 20
resolved calls for both strategy and contributed horizon; these are separate from the paper
entry-confidence gate. Observed score ticks remain immutable as the chart moves left.

## Backtesting and comparison

New backtest opens the declared native parameters for review. The screen states the backend's
saved asset, interval and dates; the live-view asset does not silently change those settings.
Use Review dates & costs or Edit roster before running when a different experiment is intended.

Existing research archives appear separately through cumulative.summary, with original source and evidence-floor summaries. They cannot enter pinned handoffs or mixed current-run comparisons without complete context.

The last completed native-session sweep is read through backtest.results. Completed results
include the arrays actually loaded, source hash, strategy parameters, code revision, CPCV geometry,
capital/fill timing and complete execution scenario. Up to twelve snapshots persist in local browser
storage, including across dashboard restarts. Canceled/failed sweeps keep their partial evidence.

Select saved runs and Compare selected runs. Compatible evidence must share data, strategy code,
interval/dates, capital/fill timing, CPCV geometry and costs. Different strategy membership is allowed.
Incompatible or partial evidence is labeled and never presented as a merged ranking or portfolio.
Median path net/Sharpe, Sharpe IQR, positive-path fraction and aggregate trade count retain their
backend meaning. Per-path drawdown/equity, itemized total fees, turnover and a matched benchmark
remain unavailable rather than being inferred from summary metrics.

## Stage a prospective paper trial

Stage paper trial retains an exact selected row and source snapshot in a browser-local draft.
It does not call prepare or run. Review pinned paper setup opens forwardtest.start with snapshot,
source_label, a visible 5-minute horizon suggestion and adaptive tuning off. Review the horizon:
a prospective forecast interval is different from the historical source bar interval.

The prepare handler verifies snapshot integrity and current strategy revision, validates the selected
strategy, and pins every execution-cost/leverage/short/confidence field. It rejects cost/asset overrides
and strategy wrappers that cannot be translated exactly. It does not modify the roster or shared
settings and starts no worker. Preparing returns a source receipt. Start prepared checks is the
separate explicit forwardtest.run operation. Ordinary unpinned paper setups remain available.

The pinned source remains in the saved native session when checking is explicitly started. A
prepared-but-not-started plan belongs to that native process. Do not treat the draft or prepare
receipt as evidence that prospective calls have been issued.

## Forward testing

The screen reads saved results for the view asset and the native session's prepared/running status.
Each row retains its trial/horizon identity. Accuracy is correct/resolved; pending calls stay outside
that denominator. Net paper return is a separate after-cost fraction displayed as a percentage.
Inspect trial shows settings, counts, costs, outcomes and available adoption notes without rewriting
history. Classification accuracy is not a calibrated profit probability; dependent observations
limit naive uncertainty intervals. A matched baseline is unavailable unless recorded evidence
supplies it.

Worker prepare/start/stop/restore actions open their registry forms. Nothing automatically resumes
when a dashboard opens. Native-session checks stop with their owner; detached compound trainers
and experiment workers retain their separate lifecycle. Stopping paper checks does not cancel real
orders or stop other components.

## Bot monitor and secondary tools

Recorder, session checks, historical sweeps, the selected-asset detached trainer and optimizer
schedule show separate liveness/output/lifetime fields. Bot grid/DCA/triangle research stays paper
simulation. Inspect links retain the affected component's actual parameters. Full standalone
executor telemetry is not currently registry-exposed and is labeled as such; existing reviewed
manual order state and reconciliation remain in Wallets & orders. Unknown submits never acquire
an automatic Retry control.

All tools keeps the complete installed command catalog, including future commands. Liquidity
mutators such as liquidity.resume are unavailable in both the list and form. Its historical reads
remain in Archive. Experiments retain their existing observed-only heatmaps and controls;
wallets/P&L/quotes and the document editor retain their existing safety contracts.

Find a tool / Command-K filters names and descriptions locally. It never calls docs.search while
typing. Explicit backend docs.search, in any mode, can check the idle index; semantic mode can also
start Ollama. That resource effect is disclosed in its form. Existing documents remain cataloged
through docs.list/read; protected evidence cannot be edited.

## Persistence and accessibility

View asset, last workspace, density, comparisons, bounded run snapshots and a paper draft use
chrome.storage.local under signalDesk.v1. Credentials, full account settings and live order
payloads are not stored there. Storage failures are visible and do not claim that a new snapshot
survives closing. Native settings and actual evidence stay authoritative for their own operations.

The interface supports keyboard navigation, local search, named dialogs with Escape/focus return,
reduced motion, wrapped mobile navigation and horizontally scrollable evidence tables. Light/dark
colors follow the browser; Compact changes density. Read timestamps do not announce every tick.
No broad permissions, side panel or runtime dependency was added. The optional side panel and
additional backend analytics adapters remain separate from the implemented full-dashboard UI.

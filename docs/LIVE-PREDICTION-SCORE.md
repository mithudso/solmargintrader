# Aggregate live prediction score

The Signal Live page in SolTUI and the extension dashboard show the same aggregate score above
the live price view and the forward-prediction table. It measures directional agreement among
eligible forward-test predictions. It is not an estimated probability or an order instruction.

A strategy configuration must have at least **60% measured forward accuracy** and **20 resolved
predictions** to vote. Each horizon it contributes must meet those same floors independently.
Missing accuracy/sample data does not qualify. Predictions must already have been issued and must
not have reached their recorded finish time. Excluded strategies stay visible in the table.

Both surfaces expose the accuracy and sample floors beside the live view. SolTUI saves them when
Enter is pressed; the dashboard saves a committed input change. They persist through `settings.save`
as `live_vote_min_accuracy` and `live_vote_min_resolved`. These display-only floors are separate
from the existing paper-execution `min_confidence=0.80` setting. The settings also appear in the dashboard's
shared TUI settings tool. An open TUI retains its loaded settings until it saves or reloads them.

## Score and labels

For each eligible strategy configuration, average its qualifying horizon votes: UP = +1, FLAT = 0,
DOWN = -1. Average those strategy means with equal weights and multiply by 100. Four horizons do
not give one strategy four times the weight of a strategy with one qualifying horizon. Round once
to one decimal before selecting the label.

| Displayed score | Label | Color |
| --- | --- | --- |
| 60 to 100 | Strong Buy | Green |
| 20 to below 60 | Buy | Green |
| Above -20 to below 20 | Flat | Gray |
| Above -60 to -20 | Sell | Red |
| -100 to -60 | Strong Sell | Red |

If no current predictions qualify, the score is unavailable (`—`) and the label is gray Flat.
It is never represented as a measured zero. The header shows the voting strategy/horizon counts
and the required floors. These are observed eligibility thresholds, not statistical proof of an edge.

## Tick history

Each new recorder quote timestamp carries the score known when that quote is observed. Later
prediction refreshes and threshold changes do not overwrite an earlier tick's score. Duplicate or
out-of-order quotes do not create extra ticks. Missing/stale evidence has a gray unavailable marker.
The score and price share fixed slots anchored at the chart's right edge; a new tick shifts both
older observations left. The visible window adapts to the available width. TUI history retains up
to 120 observations per coin, and the dashboard retains up to 600 for its selected coin. Cached
historical candle points have no retroactively assigned score.

Prediction rows refresh on the existing minute schedule. Between refreshes, both surfaces recheck
expiry and eligibility before computing the next tick's aggregate. This work does not change the
trainer, its revision hash, its stored evidence, execution settings or any order path.

## Implementation and verification

`soltui/live_score.py` reads the actual latest call and expiry per strategy/horizon, including when
multiple trainer revisions share a label. Eligibility accuracy and resolved counts belong to that
same latest trial; older winning revisions cannot qualify a newer weak or under-tested trial. It binds direction to the same call instead of taking
`MAX(direction)` across revisions. `forwardtest.predictions` exposes these timestamps, the aggregate
and the voting policy. The browser's display adapter and Python implementation run against shared
vectors in `soltui/tests/fixtures/live-score.json`.

Focused Python tests cover thresholds, missing/non-finite evidence, expiry, future issuance, equal
strategy weighting, cross-revision call identity, configuration validation, headless TUI headers
and score scrolling. Extension tests cover the same vectors and immutable timestamped history.
The Chrome gate uses an in-memory fixture to check green/red/gray headers, per-tick score labels,
leftward motion and shared-floor saving without changing real settings or submitting orders.

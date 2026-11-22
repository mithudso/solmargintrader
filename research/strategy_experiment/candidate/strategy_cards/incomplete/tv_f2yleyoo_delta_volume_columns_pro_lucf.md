---
id: tv_f2yleyoo_delta_volume_columns_pro_lucf
name: "Delta Volume Columns Pro [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Delta Volume Columns Pro [LucF]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history, level2-orderbook-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Delta Volume Columns Pro [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator displays volume​​ delta information calculated with intrabar inspection on historical bars, and feed updates when running in realtime. It is designed to run in a pane and can display either stacked buy/sell volume​ columns or a signal line which can be calculated and displayed in many different ways.

> Five different models are offered to reveal different characteristics of the calculated volume​ delta information. Many options are offered to visualize the calculations, giving you much leeway in morphing the indicator's visuals to suit your needs. If you value delta volume​ information, I hope you will find the time required to master [I]Delta Volume​ Columns Pro well worth the investment. I am confident that if you combine a proper understanding of the indicator's information with an intimate knowledge of the volume​ idiosyncrasies on the markets you trade, you can extract useful market int

> 2. When you refresh your chart or re-execute the script on the chart, the indicator will repaint because elapsed realtime bars will then recalculate as historical bars.

> The rationale behind using zero values when the bar's Buy/Sell volume​ does not exceed its EMA is to only take into account the more significant volume​.

> This balance flatlines when the bar's Buy/Sell volumes do not exceed their EMAs, which makes it useful to spot areas where trader interest dwindles, such as consolidations.

> The size of the Buy/Sell columns always represents their respective importance on the bar, but the coloring mode for tops and bottoms is independent. The default setup uses a standard coloring mode where the Buy/Sell columns are always in the bull/bear color with a higher intensity for the winning side. Seven other coloring modes allow you to pack more information in the columns. When choosing to color the top columns using a bull/bear gradient on "Average Balance", for example, you will have bull/bear colored tops. In order for the color of the bottom columns to continue to show the instant b

> The zero line can display dots when all five balances are bull/bear.

> You first select the detection mode. Divergences occur whenever the up/down direction of the signal does not match the up/down polarity of the bar. Divergences are used in three components of the indicator's visuals: the orange dot, colored chart bars, and to calculate the divergence levels on the line. The divergence levels are dynamic levels that automatically build from the line's values on divergence events. On consecutive divergences, the levels will expand, creating a channel. This implementation of the divergence levels corresponds to my view that divergences indicate anomalies, hesitat

> When a script re-executes on a chart because the browser tab is refreshed or some of its inputs are changed, elapsed realtime bars are recalculated as historical bars.

> You might prefer drastically reducing the periods of the moving averages, or using the volume​ columns mode, which displays instant values, instead of the line.

> When the script recalculates elapsed realtime bars as historical bars, the values on those bars will change, which means the script repaints in those conditions.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_volume_delta`.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history, level2-orderbook-history, synchronized-point-in-time-universe.
The complete point-in-time input set has not been verified in the repository. Do not substitute current snapshots or inferred values for historical inputs.

## Implementation and validation

No runner or registry key is assigned. Before implementation, freeze the numerical
formula, seeds, missing-value policy, warm-up and parameter domains. Where the source
does not disclose an algorithm or default, recover it rather than guessing. Specify
entry, exit, stop, holding horizon, exposure and costs separately from the indicator.
Record which choices come from the publication and which define a new experiment.

Compute with closed bars and trailing data only. Confirm pivots and higher-timeframe
values before use; never backdate a signal to a pivot that needed later bars. Test
prefix invariance, flat/zero inputs, unavailable data and one-bar-delayed execution.
Evaluate chronologically out of sample, deduct transaction and financing costs and compare with
buy-and-hold and simpler component rules. Record all searched configurations.

## Failure modes and caveats

An author description is not source code or independent validation. Visual styling,
retrospective drawing anchors, repainting pivots and fitted full-history models can
produce unavailable historical signals. A rule can be numerically correct and lose
after costs. Venue, session, data and asset differences limit transfer to SOL.

## Measured results

Not measured in this repository. Publication examples, advertised accuracy and
screenshots are not repository backtest results.

## Likelihood of success: low

Basis: a-priori. The mechanism has no confirming out-of-sample result here. This rating
does not promote the source author's claims into evidence of profitability.

## Sources

- https://www.tradingview.com/script/F2ylEYOO-Delta-Volume-Columns-Pro-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

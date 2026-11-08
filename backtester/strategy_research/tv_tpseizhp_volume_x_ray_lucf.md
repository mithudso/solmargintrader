---
id: tv_tpseizhp_volume_x_ray_lucf
name: "Volume X-ray [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Volume X-ray [LucF]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history, point-in-time-onchain-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Volume X-ray [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This tool analyzes the relative size of ​volume reported on intraday vs ​EOD (end of day) data feeds on historical bars. If you use ​​volume data to make trading decisions, it can help you improve your understanding of its nature and quality, which is especially important if you trade on intraday timeframes.

> You may elect to forego the deep dive in feed information and simply rely on the figure the indicator will calculate for the instruments you trade. One simple — and unproven — way to interpret "Volume X-ray" values is to infer that instruments with larger percentages of intraday/​EOD ​​volume ratios are more "democratic" because at intraday timeframes, you are seeing a greater proportion of the actual traded ​volume for the instrument. This could conceivably lead one to conclude that such ​​volume data is more reliable than on an instrument where intraday ​volume accounts for only 3% of ​EOD ​

> The script is very simple and has no inputs. Just add it to 1D charts and it will calculate the proportion of ​volume reported on the intraday feed over the ​​EOD ​volume. The plots show the daily values for both volumes: the teal area is the ​EOD ​volume, the orange line is the intraday ​volume. A value representing the average, cumulative intraday/​EOD ​volume percentage for the chart is displayed in the upper-right corner. Its background color changes with the percentage, with brightness levels proportional to the percentage for both the bull color (% >= 50) or the bear color (% < 50). When

> Daily and cumulative values are displayed in indicator values and the Data Window.

> The information used to build a chart's historical bars originates from data providers (exchanges, brokers, etc.) who often maintain distinct historical feeds for intraday and ​EOD timeframes. How ​volume data is assembled for intraday and ​EOD feeds varies with instruments, brokers and exchanges. Variations between the two feeds — or their absence — can be due to how instruments are traded in a particular sector and/or the ​volume reporting policy for the feeds you are using. Instruments from crypto and forex markets, for example, will often display similar ​volume on both feeds. Stocks will

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_heikin_ashi`.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history, point-in-time-onchain-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/tPsEizhp-Volume-X-ray-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

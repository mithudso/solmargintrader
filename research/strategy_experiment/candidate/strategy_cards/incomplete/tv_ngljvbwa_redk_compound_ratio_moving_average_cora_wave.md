---
id: tv_ngljvbwa_redk_compound_ratio_moving_average_cora_wave
name: "RedK Compound Ratio Moving Average (CoRa_Wave)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of RedK Compound Ratio Moving Average (CoRa_Wave); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# RedK Compound Ratio Moving Average (CoRa_Wave)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Compound Ratio Weighted Average (CoRa_Wave) is a moving average where the weights increase in a "logarithmically linear" way - from the furthest point in the data to the current point - the formula to calculate these weights work in a similar way to how "compound ratio" works - you start with an initial amount, then add a consistent "ratio of the cumulative prior sum" each period until you reach the end amount. The result is, the "step ratio" between the weights is consistent - This is not the case with linear-weights moving average (WMA), or EMA

> here are the formulas for our Compound Ratio moving average:

> index in the above formula is 0 for the furthest point out

> - for example, if you consider a Weighted Moving Average (WMA) of length 5, the weights will be (from the furthest point towards the most current) 1, 2, 3, 4, 5 -- we can see that the ratio between these weights are inconsistent. in fact, the ratio between the 2 furthest points is 2:1, but the ratio between the most recent points is 5:4 -- the ratio is inconsistent, and in fact, more recent points are not getting the best weights they should/can get to counter-act the lag effect. Using the Compound ratio approach addresses that point.

> - the outcome is, a moving average line that suffers very little lag regardless of the length, and that can be relied on to track the price movements and swings closely.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv.
The repository supports OHLCV history. Verify symbol, cadence, timezone and complete bars for the chosen experiment; this is not a claim that every source market is cached.

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

- https://www.tradingview.com/script/NgLjvBWA-RedK-Compound-Ratio-Moving-Average-CoRa-Wave/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

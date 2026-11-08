---
id: tv_d4tdeuru_volume_composition_flowly_indicators
name: "Volume composition / Flowly Indicators"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Volume composition / Flowly Indicators; not a tested trading strategy."
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
# Volume composition / Flowly Indicators

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> While net volume is useful information, it can be a blunt data point. Volume composition breaks down the content of volume, allowing a more detailed look inside each volume node. Volume composition consists of the following information:

> Buy and sell volume is defined by volume associated with lower timeframe up/down moves. This classification is further broken down to passive/active, standing for decreasing/increasing volume, e.g. a move up with volume higher than previous bar volume = active buy volume, a move up with volume lower than previous bar volume = passive buy volume.

> Timeframe settings can be changed via input menu. The lower the timeframe, the more precision you get but with the cost of less historical data and slower loading time. Users can also choose which source to use for determining buy/sell volume, e.g. using close as source, a close that is higher than previous close would be considered as buy volume. This could be replaced with OHLC4 for example, resulting in a volume direction based on OHLC average.

> Volume is arguably one of the most important data points as it directly relates to liquidity. High volume can be an indication of strength (price likely to continue moving) or absorption (price likely to halt/turn). Same applies to active volume, but with an element of aggression. High active volume serves as an indication of exuberance or otherwise forceful transacting, like stop losses triggering. With these principles in mind, the composition of volume allows distinguishing potentially important events.

> 2. Dominating volume threshold exceeded. Can be defined via input menu, 70% of total volume by default.

> 6. Dominating active volume threshold exceeded. Can be defined via input menu, 70% by default.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_volume_delta`, `tv_method_volume_footprint`.

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

- https://www.tradingview.com/script/d4TDeuRU-Volume-composition-Flowly-Indicators/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
